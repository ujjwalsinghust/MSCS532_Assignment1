def insertion_sort_descending(numbers):
    """Sort a list in place from largest to smallest."""
    for i in range(1, len(numbers)):
        key = numbers[i]
        j = i - 1

        # Move smaller elements right to make room for the key.
        while j >= 0 and numbers[j] < key:
            numbers[j + 1] = numbers[j]
            j -= 1

        numbers[j + 1] = key

    return numbers

if __name__ == "__main__":
    values = [4, 1, 7, 3, 9, 2]

    print("Original list:", values)
    insertion_sort_descending(values)
    print("Sorted list:", values)