def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    else:
        g, y, x = extended_gcd(b % a, a)
        return g, x - (b // a) * y, y

def mod_inverse(a, m):
    g, x, y = extended_gcd(a, m)
    if g != 1:
        raise Exception('modular inverse does not exist')
    else:
        return x % m

M = 900_000_000_000
P = 462746274623
print(f"P: {P}")
print(f"M: {M}")
print(f"Inverse: {mod_inverse(P, M)}")
