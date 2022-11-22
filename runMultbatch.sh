for ((i=2; i<=65536; i=i*2))
do 
	echo "NEXT NUMBER OF $i BITS"
	for (( j=1;j<=1;j++))
	do
		python3 ./QKD_ENT_batch.py "$i"	
	done
done
