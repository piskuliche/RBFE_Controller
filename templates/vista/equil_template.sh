#!/usr/bin/env bash
#SBATCH --job-name="AAA.slurm"
#SBATCH --output="AAA.slurm.slurmout"
#SBATCH --error="AAA.slumerr"
#SBATCH --partition=gh
#SBATCH --nodes=1
#SBATCH --ntasks=24
#SBATCH --time=2-00:00:00

source /work/10162/piskuliche/vista/Software/FE-Workflow/FE-Workflow.bashrc

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

	if [ ! -d t${trial} ];then mkdir t${trial}; fi

	count=-1; alllams=0
	for stage in ${eqstage[@]}; do
        	count=$((${count}+1))
        	lastcount=$((${count}-1))
		if [ "${stage}" == "init" ] || [ "${stage}" == "eqpre1P0TI" ] || [ "${stage}" == "eqpre2P0TI" ] || [ "${stage}" == "eqP0TI" ]; then continue; fi
        	laststage=${eqstage[${lastcount}]}
			# This section checks if the previous stage has completed successfully
			if grep -q "Error on OPEN" t${trial}/0.00000000_${laststage}.mdout;
                then
                        echo "ERROR - Run failed at ${laststage}"
                        echo "Exiting"
                        scancel $SLURM_JOB_ID
                else
                        echo "${laststage} okay ->"
                        echo "Proceeding with ${stage}"
                fi
        	if [ "$stage" == "minTI" ]; then alllams=1; fi

        	if [ ${alllams} -eq 0 ];then

                	if [ "$stage" == "min1" ] || [ "$stage" == "min2" ]; then
                        	# check if pmemd.cuda is present
                        	if ! command -v ${AMBERHOME}/bin/pmemd.cuda &> /dev/null; then echo "pmemd.cuda is missing." && exit 0; fi

                        	export LAUNCH="srun"
                        	export EXE=${AMBERHOME}/bin/pmemd.cuda

                        	for lam in ${endstates[@]};do
                                	echo "Running $stage for lambda ${lam}..."
                                	${EXE} -O -p ${top}/unisc.parm7 -c t${trial}/${lam}_${laststage}.rst7 -i inputs/${lam}_${stage}.mdin -o t${trial}/${lam}_${stage}.mdout -r t${trial}/${lam}_${stage}.rst7 -ref t${trial}/${lam}_${laststage}.rst7
                                	cat <<EOF2 > center.in
parm ${top}/unisc.parm7
trajin t${trial}/${lam}_${stage}.rst7
autoimage
trajout t${trial}/${lam}_${stage}_centered.rst7
go
quit
EOF2
                                	# check if cpptraj is present
                                	if ! command -v cpptraj &> /dev/null; then echo "cpptraj is missing." && exit 0; fi
                                	cpptraj < center.in
                                	sleep 1
                                	mv t${trial}/${lam}_${stage}_centered.rst7 t${trial}/${lam}_${stage}.rst7
                        	done

                	else
                        	# check if pmemd.cuda.MPI is present
                        	if ! command -v ${AMBERHOME}/bin/pmemd.cuda.MPI &> /dev/null; then echo "pmemd.cuda.MPI is missing." && exit 0; fi

                        	export LAUNCH="mpirun -np ${#endstates[@]}"
                        	export EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
                        	export MV2_ENABLE_AFFINITY=0
                        	${LAUNCH} ${EXE} -ng ${#endstates[@]} -groupfile inputs/t${trial}_${stage}.groupfile

                        	for lam in ${endstates[@]};do
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
                	fi

        	elif [ "${alllams}" == 1 ] && [ "$stage" == "minTI" ]; then

                	# check if pmemd.cuda is present
                	if ! command -v ${AMBERHOME}/bin/pmemd.cuda &> /dev/null; then echo "pmemd.cuda is missing." && exit 0; fi
                	export LAUNCH="srun"
                	export EXE=${AMBERHOME}/bin/pmemd.cuda

			firsthalf=(${lams[@]::$((${#lams[@]} / 2 ))})
			secondhalf=(${lams[@]:$((${#lams[@]} / 2 ))})

			indices=(${!secondhalf[@]}); tmp=()
			for ((k=${#indices[@]} - 1; k >= 0; k--)) ; do
				tmp+=("${secondhalf[indices[k]]}")
			done
			secondhalf=("${tmp[@]}")
			p=("${firsthalf[*]}" "${secondhalf[*]}")

			for l in ${!p[@]};do
				startingconfig=${endstates[$l]}_${preminTIstage}.rst7
				list=(${p[$l]})
				for i in ${!list[@]}; do
					lam=${list[$i]}
                        		echo "Running $stage for lambda ${lam}..."
					
					if [ "${i}" -eq 0 ]; then
						init=${startingconfig}
					else
						init=${list[$(($i-1))]}_eqP0TI.rst7
					fi

					stage=minTI
                                        ${EXE} -O -p ${top}/unisc.parm7 -c t${trial}/${init} -i inputs/${lam}_${stage}.mdin -o t${trial}/${lam}_${stage}.mdout -r t${trial}/${lam}_${stage}.rst7 -ref t${trial}/${init}
                                        sleep 1

					laststage=minTI; stage=eqpre1P0TI
                        		${EXE} -O -p ${top}/unisc.parm7 -c t${trial}/${lam}_${laststage}.rst7 -i inputs/${lam}_${stage}.mdin -o t${trial}/${lam}_${stage}.mdout -r t${trial}/${lam}_${stage}.rst7 -ref t${trial}/${lam}_${laststage}.rst7
					sleep 1

					laststage=eqpre1P0TI; stage=eqpre2P0TI
                        		${EXE} -O -p ${top}/unisc.parm7 -c t${trial}/${lam}_${laststage}.rst7 -i inputs/${lam}_${stage}.mdin -o t${trial}/${lam}_${stage}.mdout -r t${trial}/${lam}_${stage}.rst7 -ref t${trial}/${lam}_${laststage}.rst7
					sleep 1

					laststage=eqpre2P0TI; stage=eqP0TI
                        		${EXE} -O -p ${top}/unisc.parm7 -c t${trial}/${lam}_${laststage}.rst7 -i inputs/${lam}_${stage}.mdin -o t${trial}/${lam}_${stage}.mdout -r t${trial}/${lam}_${stage}.rst7 -ref t${trial}/${lam}_${laststage}.rst7
					sleep 1

                                	cat <<EOF2 > center.in
parm ${top}/unisc.parm7
trajin t${trial}/${lam}_${stage}.rst7
autoimage
trajout t${trial}/${lam}_${stage}_centered.rst7
go
quit
EOF2
                        		# check if cpptraj is present
                        		if ! command -v cpptraj &> /dev/null; then echo "cpptraj is missing." && exit 0; fi
                        		cpptraj < center.in
                        		sleep 1
                        		mv t${trial}/${lam}_${stage}_centered.rst7 t${trial}/${lam}_${stage}.rst7
                		done
				laststage=eqP0TI
			done
        	else
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
        	fi


        	if [ "${stage}" == "eqP0" ]; then
			a=0; b=0; c=0
                	for lam in ${endstates[@]};do
                        	box=($(tail -1 t${trial}/${lam}_${stage}.rst7))
                        	a=$(awk "BEGIN {print ( $a + ${box[0]} ) }")
                        	b=$(awk "BEGIN {print ( $b + ${box[1]} ) }")
                        	c=$(awk "BEGIN {print ( $c + ${box[2]} ) }")
                	done
                	a=$(awk "BEGIN {print ( $a / ${#endstates[@]} ) }")
                	b=$(awk "BEGIN {print ( $b / ${#endstates[@]} ) }")
                	c=$(awk "BEGIN {print ( $c / ${#endstates[@]} ) }")

                	a=$(printf "%8.7f" $a); b=$(printf "%8.7f" $b); c=$(printf "%8.7f" $c)
                	for lam in ${endstates[@]};do
                        	sed -e "s/ABOX/${a}/g" -e "s/BBOX/${b}/g" -e "s/CBOX/${c}/g" inputs/${lam}_eqNTP4.mdin.template > inputs/${lam}_eqNTP4.mdin
                	done
                	sleep 1
        	fi
	done
	
	# run production
	EXE=${AMBERHOME}/bin/pmemd.cuda.MPI
	echo "ready for replica ti"
done

### CUDA MPS # BEGIN ###
echo quit | nvidia-cuda-mps-control
### CUDA MPS # END ###

