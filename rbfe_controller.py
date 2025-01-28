from pathlib import Path
from glob import glob
import numpy as np
import shutil

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
    
    def write_calculation_submissions(self, aqtemplate, comtemplate, tag, trial):
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
        
        Returns
        -------
        None

        """
        self._check_edges()
        for edge in self.edges:
            edge.replace_from_template(aqtemplate, comtemplate, tag=tag, trial=trial)
        

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

        print("To submit calculation, run: \n bash submit_runs.sh")
        return
    
    def copy_edges(self, new_system):
        """ Copies the edges to a new system 
        
        Parameters
        ----------
        new_system : str
            The name of the new system
        
        Returns
        -------
        None

        """
        new_system_path = Path(new_system)
        for edge in self.edges:
            edge.copy(new_system_path)
        return

    def change_all_params(self, which="all", new_params={}):
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
            edge.change_mdin_params(which=which, new_params=new_params)
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
    
    def replace_from_template(self, aqtemplate, comtemplate, tag="equil", trial=1):
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
            check_lambda = Path(f"set_lambda_schedule/{self.name}_ar_16.txt")
            if check_lambda.exists():
                lambda_schedule = np.genfromtxt(check_lambda)
                lambda_line = " ".join([f"{x:0.8f}" for x in lambda_schedule])
                lambda_line = f"({lambda_line})\n"
            for line in content:
                if "AAA" in line:
                    line = line.replace("AAA", self.name)
                if "BBB" in line:
                    line = line.replace("BBB", str(trial))
                if check_lambda.exists():
                    if "CCC" in line:
                        line = line.replace("CCC", lambda_line)
                lines.append(line)
            if tv == 0:
                with open(self.aq / f"aq_{tag}_{trial}.sh", "w") as f:
                    f.write("".join(lines))
                self.submissions["aq"]=f"aq_{tag}_{trial}.sh"
            else:
                with open(self.com / f"{tag}_{trial}.sh", "w") as f:
                    f.write("".join(lines))
                self.submissions["com"]=f"{tag}_{trial}.sh"

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
    
    def copy(self, new_system_path):
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

            lambda_schedule = np.genfromtxt(f"set_lambda_schedule/{self.name}_ar_16.txt")
            print(f"Copying {input_dir} to {output_dir}")
            ti = NewLambdaSchedule(input_dir, output_dir, lambda_schedule=lambda_schedule, ntrials=3)
            ti.find_all_files()
            ti.write_new_lambda_schedule()
            ti.write_group_files()
        return
    
    def change_mdin_params(self, which="all", new_params={}):
        """ Replace parameters in the mdin files for the edge 
        
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
        if len(new_params.keys()) == 0:
            print("No new parameters to update.")
            return
        for sys in ["aq", "com"]:
            files = []
            if which == "all":
                files = glob(f"{self.__dict__[sys]}/inputs/*.mdin")
            else:
                files = glob(f"{self.__dict__[sys]}/inputs/*{which}.mdin")
            for file in files:
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
        state_order = ['init', 'min1', 'min2', 'eqpre1P0', 'eqpre2P0', 'eqP0', 'eqNTP4', 'eqV', 'eqP', 'eqA', 'eqProt2', 'eqProt1', 'eqProt05', 'eqProt025', 'eqProt01', 'eqProt0', 'minTI', 'eqpre1P0TI', 'eqpre2P0TI', 'eqP0TI', 'eqATI', 'preTI', 'ti']
        end_states = ['eqpre1P0', 'eqpre2P0', 'eqP0', 'eqNTP4', 'eqV', 'eqP', 'eqA', 'eqProt2', 'eqProt1', 'eqProt05', 'eqProt025', 'eqProt01', 'eqProt0']
        lambda_states = ['eqATI', 'preTI', 'ti']
        for ntrial in range(1, self.ntrials+1):
            for end_state in end_states:
                lambda_schedule = [0.00000000, 1.00000000]
                idx = state_order.index(end_state)
                out_lines = self.write_group_file_lines(lambda_schedule, prevstep=state_order[idx-1], step=end_state, ntrial=ntrial)
                with open(f"{self.output_dir}/inputs/t{ntrial}_{end_state}.groupfile", "w") as f:
                    for line in out_lines:
                        f.write(line)
            for lambda_state in lambda_states:
                idx = state_order.index(lambda_state)
                out_lines = self.write_group_file_lines(self.lambda_schedule, prevstep=state_order[idx-1], step=lambda_state, ntrial=ntrial)
                with open(f"{self.output_dir}/inputs/t{ntrial}_{lambda_state}.groupfile", "w") as f:
                    for line in out_lines:
                        f.write(line)
    
    def write_group_file_lines(self, lambda_schedule=[0.00000000,1.00000000], prevstep="eqATI", step="preTI", ntrial=1):
        out_lines = []
        for lambda_value in lambda_schedule:
            line = f"-O -p unisc.parm7 -c t{ntrial}/{lambda_value:.8f}_{prevstep}.rst7 -i inputs/{lambda_value:.8f}_{step}.mdin -o t{ntrial}/{lambda_value:.8f}_{step}.mdout -r t{ntrial}/{lambda_value:.8f}_{step}.rst7 -x t{ntrial}/{lambda_value:.8f}_{step}.nc -ref t{ntrial}/{lambda_value:.8f}_{prevstep}.rst7\n"
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
    

class ApplyRMSRestraints:
    """ Class to apply RMSD restraints to a system.
    
    Parameters
    ----------
    original_system : str
        The name of the original system
        
    """
    def __init__(self, original_system, storage_dir="avRMSD"):
        self.original_system = Calculation(original_system)
        self.original_system.find_edges()
        self.storage_dir = Path(storage_dir)
        self.inputs_dir = self.storage_dir/ "inputs"
        self.outputs_dir = self.storage_dir / "outputs"
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
        with open("cpptraj_master.sh", "w") as f:
            for line in cpptraj_master_lines:
                f.write(line)
        return
    
    def CombineAverageStructures(self):
        cpptraj_master_lines = []
        av_tgt_lines = []
        # Writes the cpptraj script to combine the average structures
        av_tgt_lines.append(f"parm {self.storage_dir}/av_tgt.rst7\n")
        for edge in self.original_system.edges:
            av_tgt_lines.append(f"parm {self.storage_dir}/av_tgt_{edge.name}.rst7\n")
        av_tgt_lines.append(f"autoimage\n")
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
        with open("cpptraj_master.sh", "w") as f:
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
        for file in glob(f"{edge.com}/inputs/*.groupfile"):
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
        for file in glob(f"{edge.com}/*.sh"):
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
        # Modify MDIN Files
        for file in glob(f"{edge.com}/inputs/*.mdin"):
            with open(file, "r") as f:
                content = f.readlines()
            with open(f"restraints_{edge.system}.in", "r") as f:
                restraints = f.readlines()
            for line in restraints:
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
            tgt_lines.append(f"trajin {edge.com}/t1/{lambda_value:.8f}_preTI.rst7\n")
        tgt_lines.append(f"average {self.storage_dir}/av_tgt_{edge.name}.rst7 '!:1,2'\n")
        tgt_lines.append("run\n")

        # Generate the ligand lines
        lig_lines.append(f"parm {edge.com}/unisc.parm7\n")
        for lambda_value in edge.endpoints:
            lig_lines.append(f"trajin {edge.com}/t1/{lambda_value:.8f}_preTI.rst7\n")
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
