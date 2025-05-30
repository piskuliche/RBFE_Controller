from pathlib import Path
from glob import glob
import numpy as np
import shutil
import subprocess

import MDAnalysis as mda

class Calculation:
    def __init__(self, system):
        self.system = system
        self.edges = []
        return
    
    def add_edge(self, edge_object):
        """ Adds an edge to the calculation 
        
        Parameters
        ----------
        edge_object : Edge
            The edge object to add to the calculation
        
        Returns
        -------
        None

        """
        self.edges.append(edge_object)

    def find_edges(self):
        """ Finds all edges in the calculation and adds them to the calculation object"""
        edgepath = Path(f"{self.system}/unified/run")
        for edge in glob(f"{edgepath}/*"):
            self.add_edge(Edge(edge, self.system))


    def _check_edges(self):
        """ Checks if there are any edges in the calculation """
        if len(self.edges) == 0:
            raise ValueError("No edges found.")
    
    def write_calculation_submissions(self, aqtemplate, comtemplate, tag, nlambda=16):
        """ Copies a template file and replaces placeholders with edge-specific values
        
        Parameters
        ----------
        aqtemplate : str
            The path to the template file for the aq folder
        comtemplate : str
            The path to the template file for the com folder
        tag : str
            The tag to use in the file name
        trial : int
            The trial number to use in the file name
        nlambda : int
            The number of lambda values to use in the calculation
        
        Returns
        -------
        None

        """
        self._check_edges()
        for edge in self.edges:
            edge.replace_from_template(aqtemplate, comtemplate, tag=tag, nlambda=nlambda)
        

    def write_network_submission(self, filename="submit_runs.sh"):
        """ Writes a submission script for all edges in the calculation 
        
        
        Parameters
        ----------
        filename : str
            The name of the submission script to write
        
        Returns
        -------
        None

        """
        self._check_edges()
        with open(filename,'w') as f:
            f.write("#!/bin/bash\n")
            for edge in self.edges:
                lines = edge.get_submission()
                for line in lines:
                    f.write(line)

        print(f"To submit calculation, run: \n bash {filename}")
        return
    
    def copy_edges(self, new_system, ntrials=1, nlambda=16):
        """ Copies the edges to a new system 
        
        Parameters
        ----------
        new_system : str
            The name of the new system
        ntrials : int
            The number of trials to copy
        nlambda : int
            The number of lambda values to use in the calculation
        
        Returns
        -------
        None

        """
        new_system_path = Path(new_system)
        for edge in self.edges:
            edge.copy(new_system_path, ntrials=ntrials, nlambda=nlambda)
        return

    def change_all_params(self, which="all", new_params={}, endpoints_only=False):
        """ Replaces parameters in the mdin files for all edges in the calculation 
        
        Parameters
        ----------
        which : str
            Which files to replace the parameters in
        new_params : dict
            The new parameters to use
        
        Returns
        -------
        None

        """
        self._check_edges()
        for edge in self.edges:
            edge.change_mdin_params(which=which, new_params=new_params, endpoints=endpoints_only)
        return



class Edge:
    """ A python class for manipulating edges in an RBFE calculation
    
    Attributes
    ----------
    self.path : Path
    self.com : Path to the com folder
    self.aq : Path to the aq folder
    self.name : str, the name of the edge in the form (Node1~Node2)
    
    """
    def __init__(self, path, system):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Path {self.path} does not exist.")
        self.com = self.path / "com"
        self.aq = self.path / "aq"
        self.name = str(self.path.name.split("/")[-1])
        self.system = str(system)
        self.submissions = {"aq": None, "com": None}
        self.endpoints = [0.00000000, 1.00000000]
    
    def replace_from_template(self, aqtemplate, comtemplate, tag="equil", nlambda=16):
        """ Replaces placeholders in a template file with edge-specific values
        
        Parameters
        ----------
        aqtemplate : str
            The path to the template file for the aq folder
        comtemplate : str
            The path to the template file for the com folder
        tag : str
            The tag to use in the file name
        trial : int
            The trial number to use in the file name
        
        Returns
        -------
        None
        """
        for tv, template in enumerate([aqtemplate, comtemplate]):
            with open(template,"r") as f:
                content = f.readlines()
            lines = []
            check_lambda = Path(f"set_lambda_schedule/{self.name}_ar_{nlambda}.txt")
            if check_lambda.exists():
                lambda_schedule = np.genfromtxt(check_lambda)
                lambda_line = " ".join([f"{x:0.8f}" for x in lambda_schedule])
                lambda_line = f"({lambda_line})\n"
            for line in content:
                if "AAA" in line:
                    line = line.replace("AAA", self.name)
                if check_lambda.exists():
                    if "CCC" in line:
                        line = line.replace("CCC", lambda_line)
                lines.append(line)
            if tv == 0:
                with open(self.aq / f"aq_{tag}.sh", "w") as f:
                    f.write("".join(lines))
                self.submissions["aq"]=f"aq_{tag}.sh"
            else:
                with open(self.com / f"{tag}.sh", "w") as f:
                    f.write("".join(lines))
                self.submissions["com"]=f"{tag}.sh"

    def get_submission(self):
        """ Returns a list of submission commands for the edge 
        
        Returns
        -------
        list
            A list of submission commands
        
        """
        lines = []
        for key in self.submissions.keys():
            if self.submissions[key] is not None:
                lines.append(f"cd {self.__dict__[key]}\n")
                lines.append(f"sbatch {self.submissions[key]}\n")
                lines.append("cd -\n")
        return lines
    
    def copy(self, new_system_path, ntrials=1, nlambda=16):
        """ Copies the edge to a new system 
        
        Parameters
        ----------
        new_system : Path
            The path to the new system
        
        Returns
        -------
        None

        """
        new_edge = new_system_path / "unified" / "run" / self.name
        for sys in ["aq","com"]:
            print("Working on ", sys)
            input_dir = self.__dict__[sys]
            output_dir = new_edge / sys
            output_dir.mkdir(parents=True, exist_ok=True)

            lambda_schedule = np.genfromtxt(f"set_lambda_schedule/{self.name}_ar_{nlambda}.txt")
            print(f"Copying {input_dir} to {output_dir}")
            ti = NewLambdaSchedule(input_dir, output_dir, lambda_schedule=lambda_schedule, ntrials=ntrials)
            ti.find_all_files()
            ti.write_new_lambda_schedule()
            ti.write_group_files()
        return
    
    def change_mdin_params(self, which="all", new_params={}, endpoints="False"):
        """ Replace parameters in the mdin files for the edge 
        
        Parameters
        ----------
        which : str
            Which files to replace the parameters in
        new_params : dict
            The new parameters to use
        endpoints : bool
            Whether to only change the endpoints
        
        Returns
        -------
        None

        """
        if len(new_params.keys()) == 0:
            print("No new parameters to update.")
            return
        for sys in ["aq", "com"]:
            files1, files2 = [], []
            if not endpoints:
                if which == "all":
                    files1 = glob(f"{self.__dict__[sys]}/inputs/*.mdin")
                else:
                    files1 = glob(f"{self.__dict__[sys]}/inputs/*{which}.mdin")
                for file in files1:
                    self.update_mdin(file, new_params)
            else:
                if which == "all":
                    files1 = glob(f"{self.__dict__[sys]}/inputs/0.00000000_*.mdin")
                    files2 = glob(f"{self.__dict__[sys]}/inputs/1.00000000_*.mdin")
                else:
                    files1 = glob(f"{self.__dict__[sys]}/inputs/0.00000000_{which}.mdin")
                    files2 = glob(f"{self.__dict__[sys]}/inputs/1.00000000_{which}.mdin")
                for file in files1:
                    self.update_mdin(file, new_params)
                for file in files2:
                    self.update_mdin(file, new_params)

        return
    
    def update_mdin(self, file, new_params):
        """ Update the mdin file with the new parameters 
        
        Parameters
        ----------
        file : str
            The path to the mdin file
        new_params : dict
            The new parameters to use
        
        """
        with open(file, "r") as f:
            content = f.readlines()
        with open(file, 'w') as f:
            for line in content:
                for key in new_params.keys():
                    if key in line:
                        line = f"{key} = {new_params[key]}\n"
                f.write(line)
        return
    


class NewLambdaSchedule:
    """ Class to handle the creation of new TI files for a given lambda schedule. 
    
    Parameters
    ----------
    input_dir : str
        The directory containing the original TI files.
    output_dir : str
        The directory to write the new TI files.
    lambda_schedule : list
        The list of lambda values to use in the new TI files.
    ntwr : int
        The number of steps to write to the restart files.
    ntpr : int
        The number of steps to write to the energies.
        
    """
    def __init__(self, input_dir, output_dir, lambda_schedule=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], ntrials=3):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.lambda_schedule = lambda_schedule
        self.ntrials = ntrials
        self.copy_directory()

    def find_all_files(self):
        """ Find all the files in the input directory. """
        self._find_files()
        self._find_endpoint_files()
        self._find_lambda_files()
        return
    
    def write_new_lambda_schedule(self):
        """ Write the new TI files with the updated lambda schedule. """
        # Do the end points first
        for file in self.endpoint_files:
            with open(file, "r") as f:
                content = f.readlines()
            with open(file.replace(str(self.input_dir), str(self.output_dir)), "w") as f:
                if "0.00000000" in file:
                    out_lines = self._rewrite_file(content, clambda="0.00000000")
                else:
                    out_lines = self._rewrite_file(content, clambda="1.00000000")
                for line in out_lines:
                    f.write(line)
        # Do the other lambda values
        #ref_lambda = str(self.lambda_files[0].split("_")[0]).split("/")[-1]
        ref_lambda = str(self.lambda_files[0].split("/")[-1].split("_")[0])
        for lambda_value in self.lambda_schedule[1:-1]:
            fmt_lambda = f"{lambda_value:.8f}"
            for file in self.lambda_files:
                with open(file, "r") as f:
                    content = f.readlines()
                with open(file.replace(ref_lambda, str(fmt_lambda)).replace(str(self.input_dir), str(self.output_dir)), "w") as f:
                    out_lines = self._rewrite_file(content, clambda=fmt_lambda)
                    for line in out_lines:
                        f.write(line)

    def copy_directory(self):
        """ Copy the input directory to the output directory. """
        ignore_pattern = shutil.ignore_patterns("*.mdout", "t*/*.mdout", "t*/*.nc")
        shutil.copytree(self.input_dir, self.output_dir, ignore=ignore_pattern, dirs_exist_ok=True)
        shutil.rmtree(f"{self.output_dir}/inputs")
        newpath = Path(f"{self.output_dir}/inputs")
        newpath.mkdir(parents=True, exist_ok=True)

    def write_group_files(self):
        state_order = ['init', 'min1', 'min2', 'eqpre1P0', 'eqpre2P0', 'eqP0', 'eqNTP4', 'eqV', 'eqP', 'eqA', 'eqProt2', 'eqProt1', 'eqProt05', 'eqProt025', 'eqProt01', 'eqProt0', 'minTI', 'eqpre1P0TI', 'eqpre2P0TI', 'eqP0TI', 'eqATI', 'eqBTI', 'preTI', 'ti']
        end_states = ['eqpre1P0', 'eqpre2P0', 'eqP0', 'eqNTP4', 'eqV', 'eqP', 'eqA', 'eqProt2', 'eqProt1', 'eqProt05', 'eqProt025', 'eqProt01', 'eqProt0']
        lambda_states = ['eqATI', 'eqBTI']
        ti_states = ['preTI', 'ti']
        for end_state in end_states:
            ep_schedule = [0.00000000, 1.00000000]
            idx = state_order.index(end_state)
            out_lines = self.write_group_file_lines(ep_schedule, prevstep=state_order[idx-1], step=end_state, tag="equil", prevtag="equil")
            with open(f"{self.output_dir}/inputs/equil_{end_state}.groupfile", "w") as f:
                for line in out_lines:
                    f.write(line)
        for lambda_state in lambda_states:
            idx = state_order.index(lambda_state)
            out_lines = self.write_group_file_lines(self.lambda_schedule, prevstep=state_order[idx-1], step=lambda_state, tag="equil", prevtag="equil")
            with open(f"{self.output_dir}/inputs/equil_{lambda_state}.groupfile", "w") as f:
                for line in out_lines:
                    f.write(line)
        for ntrial in range(1, self.ntrials+1):
            for ti_state in ti_states:
                idx = state_order.index(ti_state)
                prevtag = ""
                if ti_state == 'preTI':
                    prevtag = "equil"
                else:
                    prevtag = "ti"
                out_lines = self.write_group_file_lines(self.lambda_schedule, prevstep=state_order[idx-1], step=ti_state, tag=f"t{ntrial}", prevtag=prevtag)
                with open(f"{self.output_dir}/inputs/t{ntrial}_{ti_state}.groupfile", "w") as f:
                    for line in out_lines:
                        f.write(line)
    
    def write_group_file_lines(self, lambda_schedule=[0.00000000,1.00000000], prevstep="eqATI", step="preTI", tag="equil", prevtag="equil"):
        out_lines = []
        for lambda_value in lambda_schedule:
            line = f"-O -p unisc.parm7 -c {prevtag}/{lambda_value:.8f}_{prevstep}.rst7 -i inputs/{lambda_value:.8f}_{step}.mdin -o {tag}/{lambda_value:.8f}_{step}.mdout -r {tag}/{lambda_value:.8f}_{step}.rst7 -x {tag}/{lambda_value:.8f}_{step}.nc -ref {prevtag}/{lambda_value:.8f}_{prevstep}.rst7\n"
            out_lines.append(line)
        return out_lines
    
            

    def _rewrite_file(self, content, clambda="0.00000000"):
        """ Rewrite the file with the new lambda schedule. 
        
        Parameters
        ----------
        content : list
            The lines of the original file.
        clambda : str
            The lambda value to use in the new file.
        
        Returns
        -------
        out_lines : list
            The lines of the new file.
            
        """
        out_lines = []
        for line in content:
            if "mbar_states" in line:
                line = f"mbar_states = {len(self.lambda_schedule)}\n"
            if "mbar_lambda(" in line:
                temp = int(line.split("(")[1].split(")")[0])
                if temp <= len(self.lambda_schedule):
                    line = f"mbar_lambda({temp}) = {self.lambda_schedule[temp-1]}\n"
                else:
                    line = ""
            if "clambda" in line:
                line = f"clambda = {clambda}\n"
            out_lines.append(line)
        return out_lines

    def _find_files(self):
        """ Find all the files in the input directory"""
        self.files = glob(f"{self.input_dir}/inputs/*")
        return
    
    def _find_endpoint_files(self):
        """ Find the endpoint files in the input directory. """
        self.endpoint_files = [f for f in self.files if ("0.00000000" in f or "1.00000000" in f)]
        return
    
    def _find_lambda_files(self):
        """ Find the lambda files in the input directory. """
        # Find a single lambda value
        for file in self.files:
            if "0.00000000" not in file:
                start_name = file.split("_")[0]
                break
        self.lambda_files = []
        for file in self.files:
            if start_name in file:
                self.lambda_files.append(file)
        return
    

class RMSRestraints:
    """ Class to apply RMSD restraints to a system.
    
    Parameters
    ----------
    original_system : str
        The name of the original system
        
    """
    def __init__(self, original_system, storage_dir="avRMSD", usetraj=False):
        self.original_system = Calculation(original_system)
        self.original_system.find_edges()
        self.storage_dir = Path(storage_dir)
        self.inputs_dir = self.storage_dir/ "inputs"
        self.outputs_dir = self.storage_dir / "outputs"
        self.usetraj = usetraj
        if not self.inputs_dir.exists():
            self.inputs_dir.mkdir(parents=True, exist_ok=True)
        if not self.outputs_dir.exists():
            self.outputs_dir.mkdir(parents=True, exist_ok=True)
        

    def GetAverageStructures(self):
        """ Write the cpptraj scripts to get the average structures """
        cpptraj_master_lines = []
        for edge in self.original_system.edges:
            cpptraj_tmp = self._write_edge_ligand_lines(edge)
            cpptraj_master_lines.extend(cpptraj_tmp)
        cpptraj_master_lines.append(f"cpptraj -i {self.inputs_dir}/av_tgt.in\n")
        with open("rmsd_step1_getavstruct.sh", "w") as f:
            for line in cpptraj_master_lines:
                f.write(line)
        return
    
    def CombineAverageStructures(self):
        cpptraj_master_lines = []
        av_tgt_lines = []
        # Writes the cpptraj script to combine the average structures
        av_tgt_lines.append(f"parm {self.storage_dir}/av_tgt.parm7\n")
        for edge in self.original_system.edges:
            av_tgt_lines.append(f"trajin {self.storage_dir}/av_tgt_{edge.name}.rst7\n")
        av_tgt_lines.append(f"autoimage\n")
        av_tgt_lines.append(f"rms fit !:1,2,Na+,Cl-,WAT\n")
        av_tgt_lines.append(f"average {self.storage_dir}/av.rst7\n")
        av_tgt_lines.append("run\n")
        with open(self.inputs_dir / "av_tgt_step2.in", "w") as f:
            for line in av_tgt_lines:
                f.write(line)
        cpptraj_master_lines.append(f"cpptraj -i {self.inputs_dir}/av_tgt_step2.in\n")

        # Writes the cpptraj script to combine the ligand structures with target
        for edge in self.original_system.edges:
            av_lig_lines = []
            av_lig_lines.append(f"parm {self.storage_dir}/av_lig_{edge.name}.parm7 [CRD2]\n")
            av_lig_lines.append(f"parm {self.storage_dir}/av_tgt.parm7 [CRD1]\n")
            av_lig_lines.append(f"loadcrd {self.storage_dir}/av_lig_{edge.name}.rst7 parm av_lig_{edge.name}.parm7 CRD2\n")
            av_lig_lines.append(f"loadcrd {self.storage_dir}/av.rst7 parm {self.storage_dir}/av_tgt.parm7 CRD1\n")
            av_lig_lines.append(f"combinecrd CRD2 CRD1 parmname Parm-1-2 crdname CRD-1-2\n")
            av_lig_lines.append(f"crdout CRD-1-2 {self.outputs_dir}/av_lig_tgt_{edge.name}.rst7\n")
            av_lig_lines.append(f"run\n")
            with open(f"{self.inputs_dir}/av_lig_tgt_{edge.name}_step2.in", "w") as f:
                for line in av_lig_lines:
                    f.write(line)

            cpptraj_master_lines.append(f"cpptraj -i {self.inputs_dir}/av_lig_tgt_{edge.name}_step2.in\n")
        with open("rmsd_step_2_combine.sh", "w") as f:
            for line in cpptraj_master_lines:
                f.write(line)
        return
    
    def ApplyReferenceToSystem(self, system):
        """ Apply the reference structures to the system. 
        
        Parameters
        ----------
        system : str
            The name of the system to apply the reference structures to.
        
        """
        print("Applying reference structures to system", system)
        new_system = Calculation(system)
        new_system.find_edges()
        for edge in new_system.edges:
            print(f"Applying reference to {edge.name}")
            self._apply_reference_to_edge(edge)
        return
    
    def _apply_reference_to_edge(self, edge):
        """ Apply the reference structures to the edge. 
        
        Parameters
        ----------
        edge : Edge
            The edge to apply the reference structures to.
        
        """
        # Modify Group Files
        for file in glob(f"{edge.com}/inputs/*ti.groupfile"):
            with open(file, "r") as f:
                content = f.readlines()
            new_content = []
            for line in content:
                if "ref" in line:
                    line = line.split("-ref")[0] + f"-ref ../../../../../{self.outputs_dir}/av_lig_tgt_{edge.name}.rst7\n"
                new_content.append(line)
            with open(file, "w") as f:
                for line in new_content:
                    f.write(line)
        """
        # Modify Group Files
        for file in glob(f"{edge.com}/inputs/*preTI.groupfile"):
            with open(file, "r") as f:
                content = f.readlines()
            new_content = []
            for line in content:
                if "ref" in line:
                    line = line.split("-ref")[0] + f"-ref ../../../../../{self.outputs_dir}/av_lig_tgt_{edge.name}.rst7\n"
                new_content.append(line)
            with open(file, "w") as f:
                for line in new_content:
                    f.write(line)

        # Modify Submit Scripts
        for file in glob(f"{edge.com}/*.slurm"):
            with open(file, "r") as f:
                content = f.readlines()
            new_content = []
            for line in content:
                if "ref" in line:
                    if "echo" in line: # This is a hack to avoid the echo line in the submit script losing a quote
                        line = line.split("-ref")[0] + f'-ref ../../../../../{self.outputs_dir}/av_lig_tgt_{edge.name}.rst7"\n'
                    else:
                        line = line.split("-ref")[0] + f"-ref ../../../../../{self.outputs_dir}/av_lig_tgt_{edge.name}.rst7\n"
                new_content.append(line)
            with open(file, "w") as f:
                for line in new_content:
                    f.write(line)

        # Modify MDIN Files# Modify Submit Scripts
        for file in glob(f"{edge.com}/*.pbs"):
            with open(file, "r") as f:
                content = f.readlines()
            new_content = []
            for line in content:
                if "ref" in line:
                    if "echo" in line: # This is a hack to avoid the echo line in the submit script losing a quote
                        line = line.split("-ref")[0] + f'-ref ../../../../../{self.outputs_dir}/av_lig_tgt_{edge.name}.rst7"\n'
                    else:
                        line = line.split("-ref")[0] + f"-ref ../../../../../{self.outputs_dir}/av_lig_tgt_{edge.name}.rst7\n"
                new_content.append(line)
            with open(file, "w") as f:
                for line in new_content:
                    f.write(line)
        """

        for file in glob(f"{edge.com}/inputs/*preTI.mdin"):
            with open(file, "r") as f:
                content = f.readlines()
            with open(f"restraints_{edge.system}.in", "r") as f:
                restraints = f.readlines()
            for line in restraints:
                if len(line.split("=")) > 1:
                    line = line.split('=')[0]
                    for line2 in content:
                        if line in line2:
                            print("Removing line: ", line2)
                            content.remove(line2)
        
            with open(file, "w") as f:
                for line in content:
                    if "clambda" in line:
                        for line2 in restraints:
                            f.write(line2)
                        f.write("\n")
                    f.write(line)
        
        for file in glob(f"{edge.com}/inputs/*ti.mdin"):
            with open(file, "r") as f:
                content = f.readlines()
            with open(f"restraints_{edge.system}.in", "r") as f:
                restraints = f.readlines()
            for line in restraints:
                if len(line.split("=")) > 1:
                    line = line.split('=')[0]
                    for line2 in content:
                        if line in line2:
                            print("Removing line: ", line2)
                            content.remove(line2)
        
            with open(file, "w") as f:
                for line in content:
                    if "clambda" in line:
                        for line2 in restraints:
                            f.write(line2)
                        f.write("\n")
                    f.write(line)


        

    def _write_edge_ligand_lines(self, edge):
        """ Returns the lines for the edge-ligand restraint file 
        
        Parameters
        ----------
        edge : Edge
            The edge to use
        
        Returns
        -------
        cpptraj_master_lines : list
            The lines to write to the cpptraj master file
        
        """
        cpptraj_master_lines = []
        tgt_lines, lig_lines, av_tgt_lines, av_lig_lines = [], [], [], []
        tgt_lines.append(f"parm {edge.com}/unisc.parm7\n")
        for lambda_value in edge.endpoints:
            tgt_lines.append(f"trajin {edge.com}/t1/{lambda_value:.8f}_ti.rst7\n")
        if self.usetraj:
            tgt_lines.append(f"trajin {edge.com}/t1/{lambda_value:.8f}_ti.nc\n")
        tgt_lines.append("rms fit !:1,2,Na+,Cl-,WAT\n")
        tgt_lines.append(f"average {self.storage_dir}/av_tgt_{edge.name}.rst7 '!:1,2'\n")
        tgt_lines.append("run\n")

        # Generate the ligand lines
        lig_lines.append(f"parm {edge.com}/unisc.parm7\n")
        for lambda_value in edge.endpoints:
            lig_lines.append(f"trajin {edge.com}/t1/{lambda_value:.8f}_ti.rst7\n")
        if self.usetraj:
            lig_lines.append(f"trajin {edge.com}/t1/{lambda_value:.8f}_ti.nc\n")
        lig_lines.append("rms fit :1,2\n")
        lig_lines.append(f"average {self.storage_dir}/av_lig_{edge.name}.rst7 ':1,2'\n")
        lig_lines.append("run\n")

        # Create the tgt parm files
        av_tgt_lines.append(f"parm {edge.com}/unisc.parm7\n")
        av_tgt_lines.append("parmstrip :1,2\n")
        av_tgt_lines.append(f"parmwrite out {self.storage_dir}/av_tgt.parm7\n")
        av_tgt_lines.append("run\n")

        # Create the lig parm files
        av_lig_lines.append(f"parm {edge.com}/unisc.parm7\n")
        av_lig_lines.append(f"parmstrip !:1,2\n")
        av_lig_lines.append(f"parmwrite out {self.storage_dir}/av_lig_{edge.name}.parm7\n")
        av_lig_lines.append("run\n")

        with open(self.inputs_dir / f"tgt_{edge.name}.in", "w") as f:
            for line in tgt_lines:
                f.write(line)
        with open(self.inputs_dir / f"lig_{edge.name}.in", "w") as f:
            for line in lig_lines:
                f.write(line)
        with open(self.inputs_dir / f"av_lig_{edge.name}.in", "w") as f:
            for line in av_lig_lines:
                f.write(line)
        with open(self.inputs_dir / f"av_tgt.in", "w") as f:
            for line in av_tgt_lines:
                f.write(line)
        cpptraj_master_lines.append(f"cpptraj -i {self.inputs_dir}/tgt_{edge.name}.in\n")
        cpptraj_master_lines.append(f"cpptraj -i {self.inputs_dir}/lig_{edge.name}.in\n")
        cpptraj_master_lines.append(f"cpptraj -i {self.inputs_dir}/av_lig_{edge.name}.in\n")
        return cpptraj_master_lines


class RBFE_Analysis:
    def __init__(self, system, trials=[1], output_dir="RBFE_Analysis", subdir="analysis", num_threads=12, toolkit_bin="./"):
        self.trials=trials
        self.output_dir = Path(output_dir)
        self.subdir = self.output_dir / subdir
        self.calculation = Calculation(system)
        self.calculation.find_edges()
        self.num_threads = num_threads
        self.analysis_lines = [f"export PATH={toolkit_bin}/bin:$PATH\n", f"export PYTHONPATH={toolkit_bin}/lib/python3.11/site-packages/:$PYTHONPATH\n"]
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
        if not self.subdir.exists():
            self.subdir.mkdir(parents=True, exist_ok=True)

        return 
    def grab_data_lines(self):
        print("Grabbing data lines")
        (self.output_dir/"logs").mkdir(parents=True, exist_ok=True)
        if self.output_dir/"logs" is not None:
            shutil.rmtree(self.output_dir/"logs")
        (self.output_dir/"logs").mkdir(parents=True, exist_ok=True)
        for edge in self.calculation.edges:
            for sim_sys in ["aq", "com"]:
                for trial in self.trials:
                    analysis_dir = self.output_dir / "data"/ edge.name / sim_sys / f"{trial}"
                    if not analysis_dir.exists():
                        analysis_dir.mkdir(parents=True, exist_ok=True)
                    line=f"edgembar-amber2dats.py -r {edge.path}/{sim_sys}/remt{trial}.log --odir={analysis_dir} $(ls {edge.path}/{sim_sys}/t{trial}/*ti.mdout) > {self.output_dir}/logs/{edge.name}_{sim_sys}_t{trial}.log 2>&1 &\n"
                    self.analysis_lines.append(line)
        self.analysis_lines.append("wait\n")
        self.analysis_lines.append(f"echo 'Errors below this line:'\n")
        self.analysis_lines.append(f"grep 'Traceback' {self.output_dir}/logs/*\n")
        self.analysis_lines.append(f"echo 'End of Errors'\n")
        return
    def discover_edges(self):
        lines="""
#!/usr/bin/env python3
import edgembar
import os
from pathlib import Path

odir = Path("analysis")

s = r"data/{edge}/{env}/{trial}/efep_{traj}_{ene}.dat"
exclusions=None
edges = edgembar.DiscoverEdges(s, exclude_trials=exclusions,
target="com",
reference="aq")

if not odir.is_dir(): os.makedirs(odir)

for edge in edges:
    fname = odir / (edge.name + ".xml")
    edge.WriteXml(fname)
"""
        with open(f"{self.output_dir}/discover_edges.py", "w") as f:
            f.write(lines)
        self.analysis_lines.append(f"cd {self.output_dir}\n")
        self.analysis_lines.append("python discover_edges.py\n")
        return
    def write_edgembar(self):
        for edge in self.calculation.edges:
            line = f"OMP_NUM_THREADS={self.num_threads} edgembar_omp --halves --fwdrev analysis/{edge.name}.xml\n"
            self.analysis_lines.append(line)
        return
    def write_finalize(self):
        line = f"edgembar-WriteGraphHtml.py -o analysis/Graph.html -x ../Expt.dat $(ls analysis/*~*.py)\n"
        self.analysis_lines.append(line)
        for edge in self.calculation.edges:
            line = f"python analysis/{edge.name}.py\n"
            self.analysis_lines.append(line)
    def write(self):
        with open("analysis.sh", "w") as f:
            for line in self.analysis_lines:
                f.write(line)
        print("To run the analysis, run: \n bash analysis.sh")
        return
    
    def write_optimize(self, optimize=16, toolkit_bin=None):
        lines = []
        if toolkit_bin is not None:
            lines.append(f"export PATH={toolkit_bin}/bin:$PATH\n")
            lines.append(f"export PYTHONPATH={toolkit_bin}/lib/python3.11/site-packages/:$PYTHONPATH\n")
        optimize_dir = self.output_dir / "optimize"
        if not optimize_dir.exists():
            optimize_dir.mkdir(parents=True, exist_ok=True)
        for edge in self.calculation.edges:
            for sim_sys in ["aq", "com"]:
                for trial in self.trials:
                    line = f"fetkutils-tischedule.py --opt {optimize} --ar --ssc --plot {optimize_dir}/{edge.name}_{sim_sys}_ar_{optimize}_{trial}.png -o {optimize_dir}/{edge.name}_{sim_sys}_ar_{optimize}_{trial}.txt  {self.output_dir}/data/{edge.name}/{sim_sys}/{trial}/\n"
                    lines.append(line)
        with open("optimize.sh", "w") as f:
            for line in lines:
                f.write(line)
        print("To optimize the lambda schedule, run: \n bash optimize.sh")
        return
    
    def check_optimized(self, optimize=16):
        try:
            optimize_dir = self.output_dir / "optimize"
            opt_schedule = []
            for file in glob(f"{str(optimize_dir)}/*_{optimize}_*.txt"):
                opt_schedule.append(np.genfromtxt(file))
            if len(opt_schedule)>0:
                print("Existing optimized lambda schedules found.")
                print("Averaged Schedule: ", np.mean(opt_schedule, axis=0))
                return True
            else:
                print("No matching lambda schedule found")
                return False
        except:
            print("Exception: No matching lambda schedules found.")
            return False

def format_residues(resids):
    """ Format a list of residues into a string of ranges."""
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


def get_sel(mola, molb, mask, systemname="1Y27_rms0"):
    """ Get the selection of residues for a given edge."""
    # Load the topology and coordinate files
    parm7_file = f"{systemname}/unified/run/{mola}~{molb}/com/unisc.parm7"
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

def GenDistRestraint(distance, reference_system):
    edge_set = []
    for file in glob("avRMSD/outputs/av_lig_tgt_*~*.rst7"):
        ename = file.split("av_lig_tgt_")[-1]
        edge = ename.split(".")[0]
        mola, molb = edge.split("~")
        mask = f'element P and not (around {distance} resid 1 or around {distance} resid 2)'
        edge_set.append(get_sel(mola,molb,mask, systemname=reference_system))
    shared_elements = set.intersection(*edge_set)
    print(format_residues(list(shared_elements)))



if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser(description="Create submission scripts for RBFE calculations")
    parser.add_argument("--modify",             default=None,                   type=str, help="The system to be modified (copy edges, change parameters, etc.)")
    parser.add_argument("--reference",          default=None,                   type=str, help="A reference system (which will NOT be modified)")
    parser.add_argument("--mode",               default="help",                 type=str, help="The mode to run the script in. [help, setup, copy, update, rmsd, analysis]")
    parser.add_argument("--aq",                 default="aq_equil_template.sh", type=str, help="The template file for the aq folder")
    parser.add_argument("--com",                default="equil_template.sh",    type=str, help="The template file for the com folder")
    parser.add_argument("--tag",                default="equil",                type=str, help="The tag to use in the file name [equil or ti]")
    parser.add_argument("--toolkit_bin",        default=None,                   type=str, help="The path to the toolkit binaries")
    parser.add_argument("--change_parameters",  default=None,                   type=str, help="Which files to replace the parameters in")
    parser.add_argument("--new_parameters",     default=None,                   type=str, help="The new parameters to use in the mdin files")
    parser.add_argument("--output",             default="RBFE_Analysis",        type=str, help="The output directory for the analysis")
    parser.add_argument("--ntasks",             default=56,                     type=int, help="The number of threads to use in the analysis")
    parser.add_argument("--ntrials",            default=3,                      type=int, help="The number of trials to copy")
    parser.add_argument("--endpoints_only",     default="False",                type=str, help="Only change the endpoints")
    parser.add_argument("--nlambda",           default=16,                      type=str, help="Optimize the lambda schedule")
    parser.add_argument("--distance",          default=6,                      type=int, help="The distance to use for the distance restraints")
    parser.add_argument("--usetraj",          default=False,                  type=bool, help="Use the trajectory files for the analysis")
    args = parser.parse_args()

    if args.toolkit_bin is not None:
        with open('toolkit_bin.info','w') as f:
            f.write(args.toolkit_bin)
    
    if Path("toolkit_bin.info").exists():
        with open('toolkit_bin.info','r') as f:
            toolkit_bin = f.read().strip()
    else:
        toolkit_bin = "./"

    if args.mode == "help":
        print("The following modes are available: setup, copy, update, rmsd, analysis")
        print("setup example: python rbfe_controller.py --modify system --mode setup --aq aq_equil_template.sh --com equil_template.sh -tag equil")
        print("copy example: python rbfe_controller.py --modify system --mode copy --reference reference_system")
        print("update example: python rbfe_controller.py --modify system --mode update --change_parameters all --new_parameters '{\"nstlim\": 1000}'")
        print("update only endpoints example: python rbfe_controller.py --modify system --mode update --change_parameters all --new_parameters '{\"ntx\": 1000}' --endpoints_only True")
        print("rmsd_calc example: python rbfe_controller.py --mode rmsd_calc --reference reference_system")
        print("rmsd_apply example: python rbfe_controller.py --mode rmsd_calc --modify reference_system")
        print("analysis example: python rbfe_controller.py --reference system --mode analysis --output RBFE_Analysis --ntasks 56")
    
    if args.mode == "setup":
        if args.modify is None:
            raise ValueError("Must provide a system to modify.")
        system = Calculation(args.modify)
        system.find_edges()
        system.write_calculation_submissions(args.aq, args.com, args.tag, nlambda=args.nlambda)
        system.write_network_submission(f"submit_{args.tag}_{args.modify}.sh")

    if args.mode == "copy":
        if args.reference is None:
            raise ValueError("Must provide a reference system for the copy.")
        system = Calculation(args.reference)
        system.find_edges()
        system.copy_edges(args.modify, ntrials=args.ntrials, nlambda=args.nlambda)

    if args.mode == "update":
        if args.modify is None:
            raise ValueError("Must provide a system to modify with new parameters.")
        if args.change_parameters is None:
            raise ValueError("Must provide which parameters to change.")
        if args.new_parameters is None:
            raise ValueError("Must provide the new parameters to use.")
        if args.endpoints_only not in ["True", "False"]:
            raise ValueError("endpoints_only must be either True or False")
        endpoints_only = True if args.endpoints_only == "True" else False
        system = Calculation(args.modify)
        system.find_edges()
        new_params = json.loads(args.new_parameters)
        system.change_all_params(which=args.change_parameters, new_params=new_params, endpoints_only=endpoints_only)

    if args.mode =="rmsd_calc":
        if args.reference is None:
            raise ValueError("Must provide a reference system for the RMSD restraints.")
        rmsd = RMSRestraints(args.reference, usetraj=args.usetraj)
        print("Getting Average Structures")
        rmsd.GetAverageStructures()
        print("Combining Average Structures")
        rmsd.CombineAverageStructures()

    if args.mode =="rmsd_apply":
        if args.modify is None:
            raise ValueError("Must provide a system to modify with RMSD restraints.")
        rmsd = RMSRestraints(args.reference)
        print("Apply Reference Structures")
        rmsd.ApplyReferenceToSystem(args.modify)

    if args.mode == "dist_restraints":
        if args.reference is None:
            raise ValueError("Must provide a reference system for the distance restraints.")
        GenDistRestraint(args.distance, args.reference)

    
    if args.mode == "analysis":
        if args.reference is None:
            raise ValueError("Must provide a reference system for the analysis.")
        trials_list = list(np.arange(1, args.ntrials+1))
        analysis = RBFE_Analysis(args.reference, trials=trials_list, num_threads=args.ntasks, output_dir=args.output, toolkit_bin=toolkit_bin)
        analysis.grab_data_lines()
        analysis.discover_edges()
        analysis.write_edgembar()
        analysis.write_finalize()
        analysis.write()
        analysis.check_optimized(optimize=args.nlambda)
        analysis.write_optimize(optimize=args.nlambda, toolkit_bin=toolkit_bin)





"""
if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser(description="Create submission scripts for RBFE calculations")
    parser.add_argument("-sys", type=str, help="The system to use for the calculation")
    parser.add_argument("-aq", default="aq_equil_template.sh", type=str, help="The template file for the aq folder")
    parser.add_argument("-com", default="equil_template.sh", type=str, help="The template file for the com folder")
    parser.add_argument("-tag", default="equil", type=str, help="The tag to use in the file name [equil or ti]")
    parser.add_argument("-trial", default=1, type=int, help="The trial number to use in the file name")
    parser.add_argument("-submit", default="submit_runs.sh", type=str, help="The name of the submission script to write")
    parser.add_argument("-new", default=None, type=str, help="The name of the new system to copy the edges to")
    parser.add_argument("-change_params", default=None, type=str, help="Which files to replace the parameters in")
    parser.add_argument("-new_params", default=None, type=str, help="The new parameters to use in the mdin files")
    parser.add_argument("-rmsd", default=None, type=str, help="The original system to use for RMSD restraints")
    parser.add_argument("-analysis", default="false", type=str, help="Whether to run the analysis")
    parser.add_argument('-toolkit_bin', type=str, help="The path to the toolkit binaries")
    args = parser.parse_args()

    if args.toolkit_bin is not None:
        with open('toolkit_bin.info','w') as f:
            f.write(args.toolkit_bin)
    
    if Path("toolkit_bin.info").exists():
        with open('toolkit_bin.info','r') as f:
            toolkit_bin = f.read().strip()
    else:
        toolkit_bin = "./"
    

    
    if args.analysis == "false":
        system = Calculation(args.sys)
        system.find_edges()
        if args.new is not None:
            system.copy_edges(args.new)
        else:
            system.write_calculation_submissions(args.aq, args.com, args.tag, args.trial)
            system.write_network_submission(args.submit)
        if args.change_params is not None:
            new_params = json.loads(args.new_params)
            system.change_all_params(which=args.change_params, new_params=new_params)
        if args.rmsd is not None:
            rmsd = ApplyRMSRestraints(args.sys)
            print("Getting Average Structures")
            rmsd.GetAverageStructures()
            print("Combining Average Structures")
            rmsd.CombineAverageStructures()
            print("Apply Reference Structures")
            rmsd.ApplyReferenceToSystem(args.rmsd)
    else:
        analysis = RBFE_Analysis(args.sys, trials=[1,2,3], num_threads=56, output_dir=args.analysis, toolkit_bin=toolkit_bin)
        analysis.grab_data_lines()
        analysis.discover_edges()
        analysis.write_edgembar()
        analysis.write_finalize()
        analysis.write()

        
"""