#!/usr/bin/env bash
#SBATCH --job-name="AAA.slurm"
#SBATCH --output="AAA.slurm.slurmout"
#SBATCH --partition=rtx
#SBATCH --nodes=2
#SBATCH --ntasks=24
#SBATCH --time=0-48:00:00

source /work2/10162/piskuliche/frontera/Software/FE-Workflow/FE-Workflow.bashrc

top=${PWD}
endstates=(0.00000000 1.00000000)
lams=CCC
twostate=true
eqstage=(init min1 min2 eqpre1P0 eqpre2P0 eqP0 eqNTP4 eqV eqP eqA eqProt2 eqProt1 eqProt05 eqProt025 eqProt01 eqProt0 minTI eqpre1P0TI eqpre2P0TI eqP0TI eqATI preTI)
preminTIstage=eqProt0


### CUDA MPS # BEGIN ###
temp_path=/tmp/temp_${SLURM_JOB_ID}
mkdir -p ${temp_path}
export CUDA_MPS_PIPE_DIRECTORY=${temp_path}/nvidia-mps
export CUDA_MPS_LOG_DIRECTORY=${temp_path}/nvidia-log
nvidia-cuda-mps-control -d
### CUDA MPS # END ###

# check if AMBERHOME is set
#if [ -z "${AMBERHOME}" ]; then echo "AMBERHOME is not set" && exit 0; fi

for trial in $(seq 1 1 3); do
    #Copy the ATI files
    if [ ${trial} -gt 1 ] then;
        for lam in ${lams[@]};
        do
            cp t1/${lam}_preTI.rst7 t${trial}/${lam}_{eqATI}.rst7;
        done
    fi
    # run production
    EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
    mpirun -np ${#lams[@]} ${EXE} -ng ${#lams[@]} -groupfile inputs/t${trial}_preTI.groupfile
    echo "running replica ti"
    mpirun -np ${#lams[@]} ${EXE} -rem 3 -remlog remt${trial}.log -ng ${#lams[@]} -groupfile inputs/t${trial}_ti.groupfile
    
done

### CUDA MPS # BEGIN ###
echo quit | nvidia-cuda-mps-control
### CUDA MPS # END ###
