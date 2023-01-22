for ((i=1; i<=1000000000; i=i*5))
do 
	echo "NEXT NOISE LEVEL $i"
	python3 ./QKD_ENT.py -l 1024 -d 0.001 -n "$i"	
done
