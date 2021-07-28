#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import glob  # pragma: no cover
import meshio  # pragma: no cover
from os import path  # pragma: no cover
import subprocess  # pragma: no cover
import sys  # pragma: no cover


__all__ = ["generate_xdmf_mesh"]  # pragma: no cover


def _create_meshio_mesh(mesh, cell_type, prune_z=False):  # pragma: no cover
    """Create a meshio mesh object from a meshio mesh where only cells of
    `cell_type` are taken into account."""
    # input check
    assert isinstance(mesh, meshio.Mesh)
    assert isinstance(cell_type, str)
    assert cell_type in ("line", "triangle", "tetra")
    assert isinstance(prune_z, bool)
    # extract cells
    cells = mesh.get_cells_type(cell_type)
    # extract physical regions
    assert "gmsh:physical" in mesh.cell_data_dict
    cell_data = mesh.get_cell_data("gmsh:physical", cell_type)
    # specify data name
    if "triangle" in mesh.cells_dict and "tetra" not in mesh.cells_dict:
        if cell_type == "triangle":
            data_name = "cell_markers"
        elif cell_type == "line":
            data_name = "facet_markers"
        else:  # pragma: no cover
            raise RuntimeError()
    elif "triangle" in mesh.cells_dict and "tetra" in mesh.cells_dict:
        if cell_type == "tetra":
            data_name = "cell_markers"
        elif cell_type == "triangle":
            data_name = "facet_markers"
        else:  # pragma: no cover
            raise RuntimeError()
    else:  # pragma: no cover
        raise RuntimeError()
    # create mesh object
    out_mesh = meshio.Mesh(points=mesh.points, cells={cell_type: cells},
                           cell_data={data_name: [cell_data]})
    # remove z-component
    if prune_z:
        out_mesh.prune_z_0()
    return out_mesh


def _locate_file(basename):
    """Locate a file in the current directory.
    """
    file_extension = path.splitext(basename)[1]
    files = glob.glob("../*/*/*" + file_extension, recursive=True)
    files += glob.glob("./*/*" + file_extension, recursive=True)
    files += glob.glob("./*/*/*" + file_extension, recursive=True)
    file = None
    for f in files:
        if basename in f:
            file = f
            break
    if file is not None:
        assert path.exists(file)
    return file


def generate_xdmf_mesh(geo_file):  # pragma: no cover
    """Generates two xdmf-files from a geo-file. The two xdmf-files
    contain the mesh and the associated facet markers. Facet markers refer to
    the markers on entities of codimension one.

    The mesh is generated by calling gmsh to a generate an msh-file and the two
    xmdf-files are generated using the meshio package.
    """
    # input check
    assert isinstance(geo_file, str)
    assert path.exists(geo_file)
    assert path.splitext(geo_file)[1] == '.geo'
    basename = path.basename(geo_file)
    # generate msh file
    msh_file = _locate_file(basename.replace(".geo", ".msh"))
    if msh_file is None:
        try:
            subprocess.run(["gmsh", geo_file, "-3"], check=True)
        except subprocess.SubprocessError:  # pragma: no cover
            raise RuntimeError("GMSH is not installed on your machine and "
                               "the msh file does not exist.")
    # read msh file
    assert path.exists(msh_file)
    mesh = meshio.read(msh_file)
    # determine dimension
    if "triangle" in mesh.cells_dict and "tetra" not in mesh.cells_dict:
        assert "line" in mesh.cell_data_dict["gmsh:physical"]
        dim = 2
    elif "triangle" in mesh.cells_dict and "tetra" in mesh.cells_dict:
        assert "triangle" in mesh.cell_data_dict["gmsh:physical"]
        dim = 3
    else:  # pragma: no cover
        raise RuntimeError()
    # specify cell types
    if dim == 2:
        facet_type = "line"
        cell_type = "triangle"
        prune_z = True
    elif dim == 3:
        facet_type = "triangle"
        cell_type = "tetra"
        prune_z = False
    # extract facet mesh (codimension one)
    facet_mesh = _create_meshio_mesh(mesh, facet_type, prune_z=prune_z)
    xdmf_facet_marker_file = msh_file.replace(".msh", "_facet_markers.xdmf")
    meshio.write(xdmf_facet_marker_file, facet_mesh, data_format="XML")
    # extract facet mesh (codimension one)
    cell_mesh = _create_meshio_mesh(mesh, cell_type, prune_z=prune_z)
    xdmf_file = msh_file.replace(".msh", ".xdmf")
    meshio.write(xdmf_file, cell_mesh, data_format="XML")
    return xdmf_file, xdmf_facet_marker_file


if __name__ == "__main__":  # pragma: no cover
    generate_xdmf_mesh(sys.argv[1])
