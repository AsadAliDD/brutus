#!/bin/bash
for n in {2..12}
do
  echo "Running with -n $n"
  mpiexec -n $n --hostfile pcs.txt python3 brutus.py --algorithm md5 --path ./PasswordLists/xato-net-10-million-passwords.txt --password adf4aee6ec1729302d99457d5963181a --chunksize 100000
  clear
done