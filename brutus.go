package main

import (
	"bufio"
	"crypto/md5"
	"crypto/sha1"
	"crypto/sha256"
	"fmt"
	"hash"
	"os"
	"strings"

	"github.com/emer/empi/v2/mpi"
)

type Chunk struct {
	start int
	end   int
}

func send_string(comm *mpi.Comm, rank int, tag int, str string) {
	strBytes := []byte(str)
	strLen := len(strBytes)
	arr := make([]int, 1)
	arr[0] = strLen
	comm.SendInt(rank, tag, arr)
	comm.SendU8(rank, tag, strBytes)
}

func recv_string(comm *mpi.Comm, rank int, tag int) string {
	arr := make([]int, 1)
	comm.RecvInt(rank, tag, arr)
	strBytes := make([]byte, arr[0])
	comm.RecvU8(rank, tag, strBytes)
	return string(strBytes)
}

func send_string_array(comm *mpi.Comm, rank int, tag int, strs []string) {
	// First, send the length of the array
	arrLen := len(strs)
	arr := make([]int, 1)
	arr[0] = arrLen
	comm.SendInt(rank, tag, arr)

	// Then, send each string in the array
	for _, str := range strs {
		send_string(comm, rank, tag, str)
	}
}

func recv_string_array(comm *mpi.Comm, rank int, tag int) []string {
	// First, receive the length of the array
	arr := make([]int, 1)
	comm.RecvInt(rank, tag, arr)
	arrLen := arr[0]

	// Then, receive each string in the array
	strs := make([]string, arrLen)
	for i := 0; i < arrLen; i++ {
		strs[i] = recv_string(comm, rank, tag)
	}

	return strs
}

func hashPassword(password string, hashType string) (string, error) {

	var h hash.Hash
	switch hashType {
	case "md5":
		h = md5.New()
	case "sha1":
		h = sha1.New()
	case "sha256":
		h = sha256.New()
	default:
		return "", fmt.Errorf("invalid hash type %s", hashType)
	}

	h.Write([]byte(password))
	bs := h.Sum(nil)
	// fmt.Println(password)
	// fmt.Printf("%x\n", bs)

	return fmt.Sprintf("%x", bs), nil
}

func countLines(path string) (int, error) {
	fmt.Println("Counting lines in file: ", path)
	file, err := os.Open(path)
	if err != nil {
		return 0, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	lineCount := 0
	for scanner.Scan() {
		lineCount++
	}

	if scanner.Err() != nil {
		return 0, scanner.Err()
	}

	return lineCount, nil
}

func splitChunks(lineCount int, size int) []Chunk {

	// Naive Implementation. All processes except the root process will get the same number of lines.
	chunkSize := lineCount / size
	chunks := make([]Chunk, size)
	fmt.Println("Chunk Size: ", size)

	for i := 1; i <= size; i++ {
		start := (i - 1) * chunkSize
		end := i * chunkSize
		if i == size {
			end = lineCount
		}
		chunks[i-1] = Chunk{start, end}
		fmt.Println("Start: ", start, " End: ", end)
		//go processChunk(path, start, end)
	}
	return chunks
}

func readChunk(path string, chunk Chunk) ([]string, error) {
	file, err := os.Open(path)
	if err != nil {
		fmt.Println("Error:", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	lineCount := 0
	chunkLines := make([]string, 0)
	for scanner.Scan() {
		if lineCount >= chunk.start && lineCount < chunk.end {
			line := scanner.Text()
			line = strings.TrimSpace(line) // remove newline character
			chunkLines = append(chunkLines, line)
		}
		lineCount++
	}
	return chunkLines, nil
}

func processChunk(password string, path string, chunk []string, hashType string) string{


	password_hash, _ := hashPassword(password, hashType)
	for _, line := range chunk {

		hashed, _ := hashPassword(line, hashType)

		// fmt.Println("Line Number ", lineCount, ":", line)
		// fmt.Println("Hashed Password: ", hashed)

		if hashed == password_hash {
			fmt.Println("Password Found: ", line)
			return line
		}
	}
	return ""
}


func main() {

	/* !TODO: Add the functionality for other workers to stop if password found by one  */

	// Initialize MPI
	mpi.Init()
	defer mpi.Finalize()

	rank := mpi.WorldRank()
	size := mpi.WorldSize()
	// Send byte slice
	comm, _ := mpi.NewComm(nil)

	fmt.Println("TEST:", size, rank)

	path := "./PasswordLists/10-million-password-list-top-1000.txt"
	// path := "./PasswordLists/weakpass_3w"

	if rank == 0 {

		chunkSize := 1000

		// Sending Passowrd to all processes
		password := "music"
		for i := 1; i < size; i++ {
			send_string(comm, i, 1, password)
		}

		// Counting the Lines in the Dictionary file
		lineCount, err := countLines(path)
		if err != nil {
			fmt.Println("Error:", err)
		} else {
			fmt.Println("Number of lines:", lineCount)
		}

		if lineCount <= chunkSize {
			chunkSize = size - 1
		}

		currentChunk := 0
		chunks_queue := splitChunks(lineCount, chunkSize)

		// Initially Distribute one chunk to each process
		for i := 1; i < size; i++ {
			chunk, err := readChunk(path, chunks_queue[currentChunk])
			if err != nil {
				fmt.Println("Error in reading Chunk:", chunks_queue[currentChunk], err)
			}
			currentChunk++
			send_string_array(comm, i, 1, chunk)
		}

		// Then send the remaining chunks to the processes as they finish

		// for i := 1; i < size; i++ {
		// 	send_string_array(comm, i, 1, arr[:])
		// }

		// lineCount, err := countLines(path)
		// if err != nil {
		// 	fmt.Println("Error:", err)
		// } else {
		// 	fmt.Println("Number of lines:", lineCount)
		// }
		// chunks := splitChunks(lineCount, size)
		// fmt.Println(chunks)

		// data := make([]int, 2)
		// for i := 1; i < size; i++ {

		// 	data[0] = chunks[i-1].start
		// 	data[1] = chunks[i-1].end
		// 	fmt.Println("Sending Chunk: ", data)
		// 	comm.SendInt(i, 10, data)
		// }

	} else {

		// Recieving Password to Crack
		password := recv_string(comm, 0, 1)
		println("Received Passowrd: ", password)

		// Recieving Chunk
		chunks := recv_string_array(comm, 0, 1)
		fmt.Println("Received Chunk: ", len(chunks))

		chunk_result:=processChunk(password, path, chunks, "md5")
		if chunk_result!=""{
			fmt.Println("Password Found by Rank: ", rank, "Password: ", chunk_result)
		}

		
		// fmt.Println("Received Array: ", len(strs))

		// fmt.Println("Slave Rank: ", rank, "Received Array: ", len(chunks))

		// data := make([]int, 2)
		// comm.RecvInt(0, 10, data)

		// processChunk(password, path, Chunk{data[0], data[1]}, "md5")
		// fmt.Println("Rank ", rank, "Received Chunk: ", data[0], data[1])
	}
}
