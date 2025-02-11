#!/usr/bin/env bash
#SBATCH --job-name="com_pr_AAA.slurm"
#SBATCH --output="pr_AAA.slurm.slurmout"
#SBATCH --partition=gh
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=24
#SBATCH --time=0-48:00:00

lams=CCC
# check if AMBERHOME is set
source ~/.bashrc

### CUDA MPS # BEGIN ###
temp_path=/tmp/temp_com_AAA
mkdir -p ${temp_path}
export CUDA_MPS_PIPE_DIRECTORY=${temp_path}/nvidia-mps
export CUDA_MPS_LOG_DIRECTORY=${temp_path}/nvidia-log
nvidia-cuda-mps-control -d
### CUDA MPS # END ###



if [ -z "${AMBERHOME}" ]; then echo "AMBERHOME is not set" && exit 0; fi

for trial in $(seq 1 1 3); do

	EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
	echo "running replica ti"
	echo "mpirun -np ${#lams[@]} ${EXE} -rem 3 -remlog rem_pret${trial}.log -ng ${#lams[@]} -groupfile inputs/t${trial}_preTI.groupfile"
	mpirun -np ${#lams[@]} ${EXE} -rem 3 -remlog rempret${trial}.log -ng ${#lams[@]} -groupfile inputs/t${trial}_preTI.groupfile
	echo "mpirun -np ${#lams[@]} ${EXE} -rem 3 -remlog remt${trial}.log -ng ${#lams[@]} -groupfile inputs/t${trial}_ti.groupfile"
	mpirun -np ${#lams[@]} ${EXE} -rem 3 -remlog remt${trial}.log -ng ${#lams[@]} -groupfile inputs/t${trial}_ti.groupfile

done
### CUDA MPS # BEGIN ###
echo quit | nvidia-cuda-mps-control
### CUDA MPS # END ###

