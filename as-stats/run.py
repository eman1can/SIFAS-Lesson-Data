import os
for i in range(1, 9):
	for j in range(1, 9):
		for k in range (1, 9):
			os.system(f"curl http://as-stats.loveliv.es/detail.php?lesson={i}{j}{k} >{i}{j}{k}.html")