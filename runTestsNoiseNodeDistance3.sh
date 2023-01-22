for ((i=10000; i<=1000000000; i=i*10))
do 
	echo "NEXT NOISE LEVEL $i"
	for ((j=1; j<=100; j=j+10))
	do
	        echo "node distance of $j"
	        python3 ./QKD_ENT.py -l 1024 -d "$j" -n "$i"
	done	
done
