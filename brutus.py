from mpi4py import MPI
import hashlib
import argparse
from tqdm import tqdm
import logging
from pyfiglet import Figlet
import colorlog
from termcolor import colored
from tabulate import tabulate
import time





comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()


def setup_logger(logger_name, rank):
    """Set up logger with color support."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Choose color based on rank
    color = 'green' if rank == 0 else 'cyan'

    # Create a colored formatter
    formatter = colorlog.ColoredFormatter(
        f"%(log_color)s%(levelname)s:{logger_name}: %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': color,
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        reset=True,
        style='%'
    )

    # Create a console handler and set its formatter to the colored formatter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(handler)

    return logger


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
    # hashed_password = hash_password(password, hash_type)
    for test_password in chunk:
        if hash_password(test_password, hash_type) == password:
            return test_password
    return None

def ascii_banner():

    f = Figlet(font='univers')
    print(colored(f.renderText('BRUTUS'), 'red'))
    f_small = Figlet(font='digital')
    print(colored(f_small.renderText('A simple password cracker using MPI'), 'red'))

def parameter_table(password, hash_type, dict_file, size,lines,chunkSize):
    # Create a table for the initial logs
    table = [
        ["Password Hash", password],
        ["Hashtype", hash_type],
        ["Dictionary File", dict_file],
        ["Number of Processes", size],
        ["Total Passwords to Try", lines],
        ["ChunkSize", chunkSize]
    ]
    table_str = tabulate(table, headers=["Parameter", "Value"], tablefmt="pipe")

    # Add table boundaries and change the table color
    table_str = colored(table_str, 'green')

    # Add top and bottom borders
    border = colored('*' * (len(table_str.split('\n')[0])-5), 'green')
    table_str = border + '\n' + table_str + '\n' + border + '\n\n'

    print(table_str)

def brute_force(dict_file,password, hash_type,chunkSize):

    
    start_time = time.time()
    logger_name = 'MASTER' if rank == 0 else f'SLAVE:{rank}'
    logger = setup_logger(logger_name, rank)


    if rank==0:
        ascii_banner()
        logger.info("Starting the brute force attack with Parameters")





        # chunkSize=10000
        final_result=(None,None)
    #   Send Password and hash_type to Slave Processes
        for i in range(1, size):
            comm.send(password, dest=i,tag=1)
            comm.send(hash_type, dest=i,tag=2)

        lines=countLines(dict_file)
    #     # !Modify this later to divide the chunks evenly
        if(lines>0 and lines<=chunkSize):
            chunkSize=lines//(size-1)


            
        
        parameter_table(password, hash_type, dict_file, size,lines,chunkSize)
        # proceed = input("Do you want to proceed? (yes/no): ")
        # if proceed.lower() != "yes":
        #     return
        
        # logger.info(f"Total Passwords to Try: {lines}")
        # logger.info(f"ChunkSize: {chunkSize}")


        current_chunk=0
        # * Sending first chunk to all processes
        chunks_queue=splitChunks(lines,chunkSize)
        for i in range(1, size):
            obj=chunks_queue[current_chunk]
            # logger.info(f"Chunk Starting Line: {obj['start']},Chunk Ending Line: {obj['end']}")
            chunk_data=readChunk(dict_file,obj['start'],obj['end'])
            current_chunk+=1
            comm.send(chunk_data, dest=i,tag=3)

        # * Getting Results from Slave Processes and Distributing the next chunk
        status = MPI.Status()
        while current_chunk < len(chunks_queue):
            logger.info(f"Current Chunk: {current_chunk} out of {len(chunks_queue)}")
            result = comm.recv(source=MPI.ANY_SOURCE, tag=10,status=status)
            slave_rank = status.Get_source()
            if result[0]:
                logger.info(f"Password found: {result[1]} by Rank {slave_rank}")
                final_result = result
                # Broadcast the termination signal to all slave processes
                for i in range(1, size):
                    comm.send(None, dest=i, tag=13)
                break
            else:
                # print ("TESTTTTT")
                obj=chunks_queue[current_chunk]
                logger.info (f"Sending next chunk to Rank {slave_rank}. {obj['start']}: {obj['end']}")
                chunk_data=readChunk(dict_file,obj['start'],obj['end'])
                comm.send(chunk_data, dest=slave_rank,tag=3)
                current_chunk+=1
                # !TODO: Send the next chunk to the process that just finished

       


        # * Collect any remaining results. 
        for i in range(1, size):
            # print ("YESSS")
            result = comm.recv(source=MPI.ANY_SOURCE, tag=10)
            if result[0]:  # If the password was found
                logger.info(f"Password found by worker {i}: {result[1]}, Terminating all processes.")
                final_result = result
                for i in range(1, size):
                    comm.send(None, dest=i, tag=99)  # Sending termination signal
                break
            else:
                logger.info(f"Rank {i} did not find the password.")
        

        for i in range(1, size):
            comm.send(None, dest=i, tag=99)
        
        comm.Barrier()
        end_time = time.time()
        time_taken = end_time - start_time
        if final_result[0]:
            

            logger.info("Finishing Execution")
            table = [
                ["Password", final_result[1]],
                ["Time Taken", time_taken]
            ]
            table_str = tabulate(table, headers=["Parameter", "Value"], tablefmt="pipe")
            table_str = colored(table_str, 'green')
            border = colored('*' * (len(table_str.split('\n')[0])-5), 'green')
            table_str = '\n\n'+border + '\n' + table_str + '\n' + border + '\n\n'
            print(table_str)
        else:


            logger.info("Finishing Execution")
            table = [
                ["Password", "Not Found"],
                ["Time Taken", time_taken]
            ]
            table_str = tabulate(table, headers=["Parameter", "Value"], tablefmt="pipe")
            table_str = colored(table_str, 'red')
            border = colored('*' * (len(table_str.split('\n')[0])-5), 'red')
            table_str = '\n\n'+border + '\n' + table_str + '\n' + border + '\n\n'
            print(table_str)
    
        
    else:
        # * Slave Process

        password=comm.recv(source=0,tag=1)
        hash_type=comm.recv(source=0,tag=2)

        prcoessedChunk=1
        while True:
            chunk = comm.recv(source=0, tag=MPI.ANY_TAG)
            if chunk is None:
                logger.info("Termination Signal Recieved")
                break   
        
            
            result=processChunk(chunk,password,hash_type)
            logger.info(f"Processed Chunks: {prcoessedChunk}")
            prcoessedChunk+=1
            if result:
                logger.info(f"Password Found: {result}")
                comm.send((True,result), dest=0, tag=10)
                break
            else:
                logger.info("Password not found. Requesting next chunk")
                comm.send((False,None), dest=0, tag=10)

        # print (f"{rank} out from loop")
        comm.send((None,None),dest=0, tag=10)
        comm.Barrier()
        # print (f"{rank} sent termination signal")


    








if __name__=='__main__':

    
    parser = argparse.ArgumentParser(description="Brutus - A simple password cracker")
    parser.add_argument('--password', type=str, help="The password HASH to crack")
    parser.add_argument('--algorithm', type=str, choices=['md5', 'sha1', 'sha256'], default='sha256', help="Hash algorithm to use")
    parser.add_argument('--path', type=str, help="Path to the password list")
    parser.add_argument('--chunksize', type=int, help="Size of the chunk to be processed by each process")
    args = parser.parse_args()

    # path='./PasswordLists/10-million-password-list-top-1000.txt'
    brute_force(args.path,args.password,args.algorithm,args.chunksize)



    


