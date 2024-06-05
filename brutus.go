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
	chunkSize := lineCount / (size - 1)
	chunks := make([]Chunk, size-1)
	fmt.Println("Chunk Size: ", chunkSize)

	for i := 1; i < size; i++ {
		start := (i - 1) * chunkSize
		end := i * chunkSize
		if i == size-1 {
			end = lineCount
		}
		chunks[i-1] = Chunk{start, end}
		fmt.Println("Start: ", start, " End: ", end)
		//go processChunk(path, start, end)
	}
	return chunks
}

func processChunk(password string, path string, chunk Chunk, hashType string) {
	file, err := os.Open(path)
	if err != nil {
		fmt.Println("Error:", err)
	}
	defer file.Close()

	password_hash, _ := hashPassword(password, hashType)
	scanner := bufio.NewScanner(file)
	lineCount := 0
	for scanner.Scan() {
		lineCount++
		if lineCount >= chunk.start && lineCount < chunk.end {
			line := scanner.Text()
			line = strings.TrimSpace(line) // remove newline character

			hashed, _ := hashPassword(line, hashType)

			// fmt.Println("Line Number ", lineCount, ":", line)
			// fmt.Println("Hashed Password: ", hashed)

			if hashed == password_hash {
				fmt.Println("Password Found: ", line)
				break
			}
		}
	}
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

	if rank == 0 {

		fmt.Println("Master Process")

		// Sending Passowrd to all processes
		password := "music"
		for i := 1; i < size; i++ {
			send_string(comm, i, 1, password)
		}

		lineCount, err := countLines(path)
		if err != nil {
			fmt.Println("Error:", err)
		} else {
			fmt.Println("Number of lines:", lineCount)
		}
		chunks := splitChunks(lineCount, size)
		fmt.Println(chunks)

		data := make([]int, 2)
		for i := 1; i < size; i++ {

			data[0] = chunks[i-1].start
			data[1] = chunks[i-1].end
			fmt.Println("Sending Chunk: ", data)
			comm.SendInt(i, 10, data)
		}

	} else {
		fmt.Println("Slave Rank: ", rank)

		password := recv_string(comm, 0, 1)
		println("Received String: ", password)
		data := make([]int, 2)
		comm.RecvInt(0, 10, data)

		processChunk(password, path, Chunk{data[0], data[1]}, "md5")
		fmt.Println("Rank ", rank, "Received Chunk: ", data[0], data[1])
	}
}
