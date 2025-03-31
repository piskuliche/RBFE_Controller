import MDAnalysis as mda
import numpy as np
from glob import glob


def format_residues(resids):
    ranges = []
    start = resids[0]
    end = resids[0]

    for resid in resids[1:]:
        if resid == end + 1:
            end = resid
        else:
            if start == end:
                ranges.append(f"{start}")
            else:
                ranges.append(f"{start}-{end}")
            start = resid
            end = resid

    if start == end:
        ranges.append(f"{start}")
    else:
        ranges.append(f"{start}-{end}")

    return ",".join(ranges)


def get_sel(mola, molb, mask):
    # Load the topology and coordinate files
    parm7_file = f"1Y27_rms0/unified/run/{mola}~{molb}/com/unisc.parm7"
    rst7_file = f"avRMSD/outputs/av_lig_tgt_{mola}~{molb}.rst7"
    u = mda.Universe(parm7_file, rst7_file, topology_format="PARM7", format="RESTRT")
    t1, t2 = u.select_atoms("resid 1"), u.select_atoms("resid 2")
    # Define the selection criteria
    selection = mask

    # Select the residues within 3 Ångströms of residues 1 and 2
    selected_atoms = u.select_atoms(selection)

    selected_residues = selected_atoms.residues.resids
    # Sort and find contiguous ranges
    selected_residues = np.sort(np.unique(selected_residues))

    return set(selected_residues)



edge_set = []
for file in glob("avRMSD/outputs/av_lig_tgt_*~*.rst7"):
    ename = file.split("av_lig_tgt_")[-1]
    edge = ename.split(".")[0]
    mola, molb = edge.split("~")
    mask = 'element P and not (around 3 resid 1 or around 3 resid 2)'
    edge_set.append(get_sel(mola,molb,mask))
    print(f"Transformation {mola}~{molb}:")
    print(format_residues(list(edge_set[-1])))
shared_elements = set.intersection(*edge_set)
print(format_residues(list(shared_elements)))
                                                                                                                                       55,1          Bot