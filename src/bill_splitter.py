def split_bill(extracted_text, num_people):
    """
    Splits the total amount from the extracted receipt text among the specified number of people.
    
    :param extracted_text: The text extracted from the receipt.
    :param num_people: The number of people to split the bill.
    :return: A dictionary with the amount each person should pay.
    """
    # Example logic to extract total amount from the text
    total_amount = extract_total_amount(extracted_text)
    
    if total_amount is None or num_people <= 0:
        return "Invalid input for total amount or number of people."
    
    split_amount = total_amount / num_people
    return {f'Person {i+1}': split_amount for i in range(num_people)}

def extract_total_amount(extracted_text):
    """
    Extracts the total amount from the extracted text.
    
    :param extracted_text: The text extracted from the receipt.
    :return: The total amount as a float, or None if not found.
    """
    # Logic to find the total amount in the extracted text
    # This is a placeholder for the actual implementation
    return 100.0  # Example total amount for demonstration
