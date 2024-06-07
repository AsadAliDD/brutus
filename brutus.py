from mpi4py import MPI
import hashlib
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



def countLines(path: str) -> int:
    with open(path, 'r') as file:
        return sum(1 for line in enumerate(file))

def splitChunks(lineCount: int, chunkSize: int) -> list:

    numChunks=lineCount//chunkSize
    chunks=[]

    for i in range(0, numChunks):
        start=i * chunkSize
        end=(i+1) * chunkSize
        if i == numChunks-1:
            end = lineCount
        chunks.append({'start': start, 'end': end})
    
    print (chunks)  
    return chunks


def readChunk(path: str, start: int, end: int) -> list:
    chunk_data=[]
    with open(path, 'r') as file:
        for line_number,line in enumerate(file):
            if line_number > end:
                break
            if start <= line_number < end:
                chunk_data.append(line.strip())
    return chunk_data


def processChunk(chunk: list, password: str, hash_type: str) -> str:
    hashed_password = hash_password(password, hash_type)
    for test_password in chunk:
        if hash_password(test_password, hash_type) == hashed_password:
            return test_password
    return None

def brute_force(dict_file,password, hash_type):

    if rank==0:

        chunkSize=5000
    #   Send Password and hash_type to Slave Processes
        for i in range(1, size):
            comm.send(password, dest=i,tag=1)
            comm.send(hash_type, dest=i,tag=2)

        lines=countLines(dict_file)

        print (f"{lines},{chunkSize}")
    #     # !Modify this later to divide the chunks evenly
        if(lines>0 and lines<=chunkSize):
            chunkSize=size-1
            print (chunkSize)

        current_chunk=0
        # * Sending first chunk to all processes
        chunks_queue=splitChunks(lines,chunkSize)
        for i in range(1, size):
            obj=chunks_queue[current_chunk]
            print (obj['start'],obj['end'])
            chunk_data=readChunk(dict_file,obj['start'],obj['end'])
            current_chunk+=1
            comm.send(chunk_data, dest=i,tag=3)

        # * Getting Results from Slave Processes and Distributing the next chunk
        status = MPI.Status()
        while current_chunk < len(chunks_queue):
            print (f"Current Chunk: {current_chunk} out of {len(chunks_queue)}")
            result = comm.recv(source=MPI.ANY_SOURCE, tag=10,status=status)
            slave_rank = status.Get_source()
            if result[0]:
                print(f"MASTER: Password found: {result[1]} by Rank {slave_rank}")
                # Broadcast the termination signal to all slave processes
                for i in range(1, size):
                    comm.send(None, dest=i, tag=13)
                break
            else:
                # print ("TESTTTTT")
                obj=chunks_queue[current_chunk]
                print (f"Sending next chunk to Rank {slave_rank}. {obj['start']}: {obj['end']}")
                chunk_data=readChunk(dict_file,obj['start'],obj['end'])
                comm.send(chunk_data, dest=slave_rank,tag=3)
                current_chunk+=1
                # !TODO: Send the next chunk to the process that just finished

       


        # * Collect any remaining results. 
        for i in range(1, size):
            print ("YESSS")
            result = comm.recv(source=MPI.ANY_SOURCE, tag=10)
            if result[0]:  # If the password was found
                print(f"MASTER: Password found by worker {i}: {result[1]}, terminating all processes.")
                for i in range(1, size):
                    comm.send(None, dest=i, tag=99)  # Sending termination signal
                break
            else:
                print(f"MASTER: Rank {i} did not find the password.")
        

        for i in range(1, size):
            comm.send(None, dest=i, tag=99)
    
        
    else:
        # * Slave Process

        password=comm.recv(source=0,tag=1)
        hash_type=comm.recv(source=0,tag=2)

        prcoessedChunk=1
        while True:
            chunk = comm.recv(source=0, tag=MPI.ANY_TAG)
            if chunk is None:
                print (f"Rank {rank} received termination signal")
                break   
            print ("Rank: ",rank, "Processed Chunks: ",prcoessedChunk,"Password: ",password,"Hash Type: ",hash_type)

            prcoessedChunk+=1
            result=processChunk(chunk,password,hash_type)
            if result:
                print (f"Rank {rank} found the password: {result}")
                comm.send((True,result), dest=0, tag=10)
                break
            else:
                print (f"Rank {rank} did not find the password")
                comm.send((False,None), dest=0, tag=10)

        print (f"{rank} out from loop")
        comm.send((None,None),dest=0, tag=10)
        print (f"{rank} sent termination signal")









if __name__=='__main__':


    parser = argparse.ArgumentParser(description="Brutus - A simple password cracker")
    parser.add_argument('--password', type=str, help="The password to crack")
    parser.add_argument('--algorithm', type=str, choices=['md5', 'sha1', 'sha256'], default='sha256', help="Hash algorithm to use")
    args = parser.parse_args()

    # path='./PasswordLists/10-million-password-list-top-1000.txt'
    path='./PasswordLists/10-million-password-list-top-1000000.txt'
    brute_force(path,args.password,args.algorithm)



    


