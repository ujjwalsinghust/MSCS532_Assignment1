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



assert insertion_sort_descending([]) == []
assert insertion_sort_descending([5]) == [5]
assert insertion_sort_descending([3, 1, 3]) == [3, 3, 1]
assert insertion_sort_descending([-2, 0, -5]) == [0, -2, -5]
print("All tests passed.")