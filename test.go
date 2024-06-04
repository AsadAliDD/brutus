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

	"github.com/marcusthierfelder/mpi"
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

			fmt.Println("Line Number ", lineCount, ":", line)
			fmt.Println("Hashed Password: ", hashed)

			if hashed == password_hash {
				fmt.Println("Password Found: ", line)
				break
			}
		}
	}
}

func main() {

	// Initialize MPI
	mpi.Init()

	size := mpi.Comm_size(mpi.COMM_WORLD)
	rank := mpi.Comm_rank(mpi.COMM_WORLD)

	fmt.Println(size, rank)

	// password := "music"
	path := "./PasswordLists/10-million-password-list-top-1000.txt"

	if rank == 0 {

		fmt.Println("Master Process")
		lineCount, err := countLines(path)
		if err != nil {
			fmt.Println("Error:", err)
		} else {
			fmt.Println("Number of lines:", lineCount)
		}

		chunks := splitChunks(lineCount, size)
		fmt.Println(chunks)

		data := make([]int, size)
		for i := 1; i < size; i++ {
			data[0] = chunks[i-1].start
			data[1] = chunks[i-1].end
			fmt.Println("Sending Chunk: ", data)
			mpi.Send_int(data, i, 10, mpi.COMM_WORLD)
		}

	} else {
		fmt.Println("Slave Rank: ", rank)

		data := make([]int, size)
		mpi.Recv_int(data, 0, 10, mpi.COMM_WORLD)
		fmt.Println("Rank ", rank, "Received Chunk: ", data[0], data[1])
	}

	mpi.Finalize()

	// if rank == 0 {
	// 	fmt.Println("Rank: ", rank, " Size: ", size)
	// } else {
	// 	fmt.Println("Rank: ", rank)
	// }

	// chunks := splitChunks(lineCount, 4)
	// fmt.Println(chunks)

	// processChunk("music", path, chunks[1], "md5")

	// passHash, _ := hashPassword("asad.101", "md5")
	// fmt.Println(passHash)
}
