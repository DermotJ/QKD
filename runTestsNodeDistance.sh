for ((i=0; i<=1000; i=i+10))
do 
	echo "node distance of $i"
	python3 ./QKD_ENT.py -l 1024 -d "$i" 	
done
