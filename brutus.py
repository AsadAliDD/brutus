from mpi4py import MPI
import hashlib
import numpy as np
import argparse
from tqdm import tqdm
import logging


comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
logging.basicConfig(level=logging.INFO)

# Hashing function
def hash_password(password, hash_type):
    hash_func = hashlib.new(hash_type)
    hash_func.update(password.encode('utf-8'))
    return hash_func.hexdigest()



def read_password_list(path):
    with open(path, 'r') as file:
        dictionary = [line.strip() for line in file.readlines()]
    return dictionary




def distribute_password_list(path, password,hash_type='sha256'):

    found=False
    if rank == 0:
        # Determine the number of lines in the file
        with open(path) as f:
            for i, _ in enumerate(f):
                pass
        num_lines = i + 1
        print (f"Number of lines in the file: {num_lines}")

        # Calculate the number of passwords each process should handle
        chunk_size = num_lines // (size -1)
        remainder = num_lines % (size -1)

        print (f"Chunk size: {chunk_size}")
        print (f"Remainder: {remainder}")




    #    Send Password to Slave Processes
        for i in range(1, size):
            comm.send(password, dest=i)

        # Instead of Sending the entire file to each process, we will send the start and end lines of the file to each process
        for i in range(1, size):
            # Calculate the start and end lines for this chunk
            start_line = (i - 1) * chunk_size
            end_line = start_line + chunk_size
            # Add one more line to the last chunk if the number of lines is not evenly divisible by the number of processes
            if i == size - 1 and remainder != 0:
                end_line += remainder

            print (f"Rank {rank} sending to rank {i} -- lines {start_line} to {end_line}")
            comm.send((start_line, end_line), dest=i)

        # for i in range(1, size):
        #     found=comm.recv(source=i,tag=12)
        #     if found:
        #         print (f"Password found by Rank {i}")
                
        #         break
        


        # Wait for a result from any process
        while not found:
            found = comm.recv(source=MPI.ANY_SOURCE, tag=12)
            if found:
                found_password = comm.recv(source=MPI.ANY_SOURCE, tag=13)
                print(f"Password found: {found_password}")
                # Broadcast the termination signal to all slave processes
                for i in range(1, size):
                    comm.send(True, dest=i, tag=12)
                break

  
    else:



        password=comm.recv(source=0)
        password=hash_password(password, hash_type)
        # Receive the start and end lines from the root process
        start_line, end_line = comm.recv(source=0)
        print (f"Rank {rank} received -- lines {start_line} to {end_line}")

        total_tested=0
        with open(path) as f:
            for i, line in enumerate(f):
                if i >= start_line and i < end_line:
                    total_tested+=1
                    print(f"Rank {rank} testing password: {total_tested}")
                    if comm.Iprobe(source=0, tag=12):
                        found = comm.recv(source=0, tag=12)
                        print (f"Rank {rank} Password found by another process")
                        break
                    else:
                        pass_to_try = hash_password(line.strip(),hash_type)
                        if password == pass_to_try:
                            print(f"Rank {rank} found the password: {line.strip()}")
                            found = True
                            comm.send(found, dest=0, tag=12)
                            comm.send(line.strip(), dest=0, tag=13)
                            # comm.send(found,dest=0,tag=12)
                            # comm.bcast(found, root=0)
                            break


        # Send termination signal
        if not found:
            found = comm.send(found,dest=0,tag=12)
            # found = comm.bcast(found, root=0)






def brute_force(password, hash_type):

    found=False

    if rank==0:


        pass_list=read_password_list('./PasswordLists/10-million-password-list-top-1000.txt')
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
            logging.info('Password not found by any process.')
            # print("Password not found by any process.")
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


   

    distribute_password_list('./PasswordLists/10-million-password-list-top-1000.txt', args.password,args.algorithm)
    # brute_force(args.password, args.algorithm)
    # dict=read_password_list('./PasswordLists/10-million-password-list-top-1000.txt')
    # print (dict)
    # Get the password from the user
    # password = input("Enter the password: ")
    # hash_type = input("Enter the hash type: ")
    # print(f"Hashed password: {hash_password(password, hash_type)}")



