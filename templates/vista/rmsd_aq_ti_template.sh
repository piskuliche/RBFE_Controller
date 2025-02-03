#!/usr/bin/env bash
#SBATCH --job-name="AAA.slurm"
#SBATCH --output="AAA.slurm.slurmout"
#SBATCH --error="AAA.slurm.slurmerr"
#SBATCH --partition=gh
#SBATCH --nodes=1
#SBATCH --ntasks=24
#SBATCH --time=2-00:00:00

source /work/10162/piskuliche/vista/Software/FE-Workflow/FE-Workflow.bashrc

top=${PWD}
endstates=(0.00000000 1.00000000)
lams=CCC
twostate=true
eqstage=(init min1 min2 eqpre1P0 eqpre2P0 eqP0 eqNTP4 eqV eqP eqA minTI eqpre1P0TI eqpre2P0TI eqP0TI eqATI preTI)
preminTIstage=eqA
reference_system=1Y27_2


### CUDA MPS # BEGIN ###
temp_path=/tmp/temp_${SLURM_JOB_ID}
mkdir -p ${temp_path}
export CUDA_MPS_PIPE_DIRECTORY=${temp_path}/nvidia-mps
export CUDA_MPS_LOG_DIRECTORY=${temp_path}/nvidia-log
nvidia-cuda-mps-control -d
### CUDA MPS # END ###
#if [ -z "${AMBERHOME}" ]; then echo "AMBERHOME is not set" && exit 0; fi
trial=1

stage=preTI
for lam in ${lams[@]}; do cp ../../../../../${reference_system}/unified/run/AAA/aq/t${trial}/${lam}_eqATI.rst7 t${trial}/; done
# check if pmemd.cuda.MPI is present
                        if ! command -v ${AMBERHOME}/bin/pmemd.cuda.MPI &> /dev/null; then echo "pmemd.cuda.MPI is missing." && exit 0; fi

                        export LAUNCH="mpirun -np ${#lams[@]}"
                        export EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
                        export MV2_ENABLE_AFFINITY=0
                        ${LAUNCH} ${EXE} -ng ${#lams[@]} -groupfile inputs/t${trial}_${stage}.groupfile

                        for lam in ${lams[@]};do
                                cat <<EOF2 > center.in
parm ${top}/unisc.parm7
trajin t${trial}/${lam}_${stage}.rst7
autoimage
trajout t${trial}/${lam}_${stage}_centered.rst7
go
quit
EOF2
                                if ! command -v cpptraj &> /dev/null; then echo "cpptraj is missing." && exit 0; fi
                                cpptraj < center.in
                                sleep 1
                                mv t${trial}/${lam}_${stage}_centered.rst7 t${trial}/${lam}_${stage}.rst7
                        done




# run production
EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
echo "running replica ti"
mpirun -np ${#lams[@]} ${EXE} -rem 3 -remlog remt${trial}.log -ng ${#lams[@]} -groupfile inputs/t${trial}_ti.groupfile


trial=2

stage=preTI
for lam in ${lams[@]}; do cp ../../../../../${reference_system}/unified/run/AAA/aq/t${trial}/${lam}_eqATI.rst7 t${trial}/; done
# check if pmemd.cuda.MPI is present
                        if ! command -v ${AMBERHOME}/bin/pmemd.cuda.MPI &> /dev/null; then echo "pmemd.cuda.MPI is missing." && exit 0; fi

                        export LAUNCH="mpirun -np ${#lams[@]}"
                        export EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
                        export MV2_ENABLE_AFFINITY=0
                        ${LAUNCH} ${EXE} -ng ${#lams[@]} -groupfile inputs/t${trial}_${stage}.groupfile

                        for lam in ${lams[@]};do
                                cat <<EOF2 > center.in
parm ${top}/unisc.parm7
trajin t${trial}/${lam}_${stage}.rst7
autoimage
trajout t${trial}/${lam}_${stage}_centered.rst7
go
quit
EOF2
                                if ! command -v cpptraj &> /dev/null; then echo "cpptraj is missing." && exit 0; fi
                                cpptraj < center.in
                                sleep 1
                                mv t${trial}/${lam}_${stage}_centered.rst7 t${trial}/${lam}_${stage}.rst7
                        done




# run production
EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
echo "running replica ti"
mpirun -np ${#lams[@]} ${EXE} -rem 3 -remlog remt${trial}.log -ng ${#lams[@]} -groupfile inputs/t${trial}_ti.groupfile

trial=3

stage=preTI
for lam in ${lams[@]}; do cp ../../../../../${reference_system}/unified/run/AAA/aq/t${trial}/${lam}_eqATI.rst7 t${trial}/; done
# check if pmemd.cuda.MPI is present
                        if ! command -v ${AMBERHOME}/bin/pmemd.cuda.MPI &> /dev/null; then echo "pmemd.cuda.MPI is missing." && exit 0; fi

                        export LAUNCH="mpirun -np ${#lams[@]}"
                        export EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
                        export MV2_ENABLE_AFFINITY=0
                        ${LAUNCH} ${EXE} -ng ${#lams[@]} -groupfile inputs/t${trial}_${stage}.groupfile

                        for lam in ${lams[@]};do
                                cat <<EOF2 > center.in
parm ${top}/unisc.parm7
trajin t${trial}/${lam}_${stage}.rst7
autoimage
trajout t${trial}/${lam}_${stage}_centered.rst7
go
quit
EOF2
                                if ! command -v cpptraj &> /dev/null; then echo "cpptraj is missing." && exit 0; fi
                                cpptraj < center.in
                                sleep 1
                                mv t${trial}/${lam}_${stage}_centered.rst7 t${trial}/${lam}_${stage}.rst7
                        done




# run production
EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
echo "running replica ti"
mpirun -np ${#lams[@]} ${EXE} -rem 3 -remlog remt${trial}.log -ng ${#lams[@]} -groupfile inputs/t${trial}_ti.groupfile

### CUDA MPS # BEGIN ###
echo quit | nvidia-cuda-mps-control
### CUDA MPS # END ###
 
