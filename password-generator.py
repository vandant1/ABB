import hashlib
import os
import base64

def generate_scrypt_hash(password, N=16384, r=8, p=1, salt_length=16, dklen=64):
    """
    Generates a scrypt hash string in the format: scrypt:N:r:p$salt$hash.

    Args:
        password (str): The plaintext password to hash.
        N (int): CPU/Memory cost parameter. Must be a power of 2.
        r (int): Block size parameter.
        p (int): Parallelization parameter.
        salt_length (int): Length of the random salt to generate in bytes.
        dklen (int): Desired key length (output hash length) in bytes.

    Returns:
        str: The scrypt hash string.
    """
    # 1. Generate a random salt
    # os.urandom provides cryptographically strong random bytes.
    salt = os.urandom(salt_length)

    # 2. Derive the key using hashlib.scrypt
    # The 'hashlib.scrypt' function returns bytes.
    derived_key = hashlib.scrypt(
        password.encode('utf-8'),  # Password must be bytes
        salt=salt,
        n=N,
        r=r,
        p=p,
        maxmem=0,  # 0 means no memory limit, relies on N, r for memory
        dklen=dklen
    )

    # 3. Base64 encode the salt and the derived key for string representation
    # Base64.urlsafe_b64encode ensures characters are safe for URLs/filenames
    # .decode('utf-8') converts bytes back to string for concatenation
    encoded_salt = base64.urlsafe_b64encode(salt).decode('utf-8').rstrip('=')
    encoded_derived_key = base64.urlsafe_b64encode(derived_key).decode('utf-8').rstrip('=')

    # 4. Assemble the final hash string
    scrypt_hash_string = f"scrypt:{N}:{r}:{p}${encoded_salt}${encoded_derived_key}"

    return scrypt_hash_string

def verify_scrypt_hash(password, hashed_password_string):
    """
    Verifies a plaintext password against a scrypt hash string.

    Args:
        password (str): The plaintext password to verify.
        hashed_password_string (str): The scrypt hash string to compare against.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    parts = hashed_password_string.split('$')
    if len(parts) != 3:
        print("Invalid hash format.")
        return False

    prefix_params = parts[0].split(':')
    if len(prefix_params) != 4 or prefix_params[0] != 'scrypt':
        print("Invalid scrypt prefix or parameters.")
        return False

    try:
        N = int(prefix_params[1])
        r = int(prefix_params[2])
        p = int(prefix_params[3])
    except ValueError:
        print("Invalid numeric parameters (N, r, p).")
        return False

    encoded_salt = parts[1]
    expected_encoded_derived_key = parts[2]

    # Add padding back if it was stripped
    salt = base64.urlsafe_b64decode(encoded_salt + '==' * (len(encoded_salt) % 4))
    expected_derived_key = base64.urlsafe_b64decode(expected_encoded_derived_key + '==' * (len(expected_encoded_derived_key) % 4))

    # Re-derive the key using the extracted parameters and salt
    try:
        re_derived_key = hashlib.scrypt(
            password.encode('utf-8'),
            salt=salt,
            n=N,
            r=r,
            p=p,
            maxmem=0,
            dklen=len(expected_derived_key) # Ensure we derive with the same output length
        )
    except Exception as e:
        print(f"Error during re-derivation: {e}")
        return False

    # Compare the newly derived key with the stored derived key
    # Use hmac.compare_digest for constant-time comparison to prevent timing attacks
    return hashlib.compare_digest(re_derived_key, expected_derived_key)


# --- Example Usage ---
if __name__ == "__main__":
    my_password = "vandan@123"

    print(f"Original Password: {my_password}")

    # Generate a hash with default parameters (N=32768, r=8, p=1)
    hashed_password = generate_scrypt_hash(my_password)
    print(f"Generated Scrypt Hash: {hashed_password}")

    # Verify the password
    is_correct = verify_scrypt_hash(my_password, hashed_password)
    print(f"Verification successful: {is_correct}")

    # Test with a wrong password
    wrong_password = "wrongPassword"
    is_wrong = verify_scrypt_hash(wrong_password, hashed_password)
    print(f"Verification with wrong password: {is_wrong}")

    # Example of a hash you might want to verify (similar to your provided one)
    # Note: The salt and hash part will be different because they are randomly generated.
    # The `dklen` (derived key length) for the example you provided would be 64 bytes
    # because '7d6c9a8b5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d'
    # is 128 hex characters, which is 64 bytes.
    example_password = "testpassword"
    example_hash_string = generate_scrypt_hash(example_password, N=32768, r=8, p=1, salt_length=16, dklen=64)
    print(f"\nExample specific hash: {example_hash_string}")
    print(f"Verification of example hash: {verify_scrypt_hash(example_password, example_hash_string)}")
    print(f"Verification of example hash (wrong pass): {verify_scrypt_hash('wrong', example_hash_string)}")