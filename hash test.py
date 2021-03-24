addresses = ["80:EA:CA:70:00:03", "80:EA:CA:70:00:04"]
# addresses = ["80:EA:CA:70:00:04"]
address_hash_table = {}
address_byte_array = 0x00

for address in addresses:
    address_byte_array = bytearray.fromhex(address.replace(":", ""))
    address_byte_array.reverse()

    # Initialize with some random large-ish prime
    hashed_address = 5381
    for b in address_byte_array:
        hashed_address = ((hashed_address << 5) + hashed_address) + b

    print(hashed_address)
    address_hash_table[address] = hashed_address

# djb2 hashing algorithm to create a 2 byte (aka sizeof(int16_t)) hash from a 6 byte address


# hashAddress = 5381;
# for (counter = 0; word[counter]!='\0'; counter++){
#     hashAddress = ((hashAddress << 5) + hashAddress) + word[counter];
# }