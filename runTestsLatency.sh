for ((i=100000000; i<=1000000000000; i=i*2))
do 
	echo "Latency LEVEL $i"
	python3 ./QKD_ENT.py -l 1024 -d 0.001 -t "$i"	
done
