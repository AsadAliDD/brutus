from mpi4py import MPI
import hashlib
import numpy as np
import argparse
from tqdm import tqdm


comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Hashing function
def hash_password(password, hash_type):
    hash_func = hashlib.new(hash_type)
    hash_func.update(password.encode('utf-8'))
    return hash_func.hexdigest()



def read_password_list(path):
    with open(path, 'r') as file:
        dictionary = [line.strip() for line in file.readlines()]
    return dictionary



def brute_force(password, hash_type):

    found=False

    if rank==0:


        pass_list=read_password_list('./PasswordLists/10-million-password-list-top-1000000.txt')
        password=hash_password(password, hash_type)

        # Partition dictionary into Number of Processes - 1. The rank 0 process will not be used for computation. 
        pass_chunks = np.array_split(pass_list, size - 1)
        

        # Distribute dictionary chunks to slave processes
        for i in range(1, size):
            comm.send(password, dest=i, tag=10)

        # Distribute dictionary chunks to slave processes
        for i in range(1, size):
            comm.send(pass_chunks[i-1], dest=i, tag=11)

     
        # Receive found variable from each slave process
        for i in range(1, size):
            found = comm.recv(source=i, tag=12)
            if found:
                break

        # Check if password was not found by any process
        if not found:
            print("Password not found by any process.")
    else:
        # Receive dictionary chunks from master process
        password = comm.recv(source=0, tag=10)
        pass_list = comm.recv(source=0, tag=11)
        print (f"{rank} received {len(pass_list)} Passwords to try")


        for test_password in tqdm(pass_list, desc=f"Testing passwords: {rank}", unit="password"):

            if found:
                break
        
            if password == hash_password(test_password, hash_type):
                print(f"Rank {rank} found the password: {test_password}")
                found = True
                comm.send(found,dest=0, tag=12)
                break

             # Listen for termination signal
        if not found:
            found = comm.send(found,dest=0, tag=12)

    




if __name__=='__main__':


    parser = argparse.ArgumentParser(description="Brutus - A simple password cracker")
    parser.add_argument('--password', type=str, help="The password to crack")
    parser.add_argument('--algorithm', type=str, choices=['md5', 'sha1', 'sha256'], default='sha256', help="Hash algorithm to use")
    args = parser.parse_args()


   


    brute_force(args.password, args.algorithm)
    # dict=read_password_list('./PasswordLists/10-million-password-list-top-1000.txt')
    # print (dict)
    # Get the password from the user
    # password = input("Enter the password: ")
    # hash_type = input("Enter the hash type: ")
    # print(f"Hashed password: {hash_password(password, hash_type)}")



