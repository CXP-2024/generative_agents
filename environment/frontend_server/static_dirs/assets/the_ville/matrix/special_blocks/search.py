import os
import csv

def extract_numbers_from_csv(folder_path):
    numbers = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, 'r') as csvfile:
                csv_reader = csv.reader(csvfile)
                for row in csv_reader:
                    try:
                        number = int(row[0])  # Convert to float to handle decimals
                        numbers.append(number)
                    except (ValueError, IndexError):
                        # Handle cases where the first element is not a number or the row is empty
                        pass
    return numbers

def find_missing_numbers(numbers):
    if not numbers:
        return []

    min_num = min(numbers)
    max_num = max(numbers)
    all_numbers = set(range(min_num - 1, max_num + 2))
    present_numbers = set(numbers)
    missing_numbers = sorted(list(all_numbers - present_numbers), key=lambda x: [int(d) for d in str(x).zfill(5)][::-1])
    return missing_numbers

if __name__ == '__main__':
    folder_path = "."  # Replace with the actual path to your folder
    extracted_numbers = extract_numbers_from_csv(folder_path)
    missing_numbers = find_missing_numbers(extracted_numbers)
    print("Missing numbers:", missing_numbers)