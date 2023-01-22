for ((i=1; i<=1000000000; i=i*5))
do 
	echo "NEXT NOISE LEVEL $i"
	for ((j=0; j<=10000; j=j+1000))
	do
	        echo "node distance of $j"
	        python3 ./QKD_ENT.py -l 1024 -d "$j" -n "$i"
	done	
done
