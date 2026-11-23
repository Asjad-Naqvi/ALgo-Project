class MinHeap:
    def __init__(self):
        self.heap = []

    def push(self, item):
        self.heap.append(item)
        i = len(self.heap) - 1

        while i > 0:
            parent = (i - 1) // 2

            if self.heap[parent][:2] <= item[:2]:
                break

            self.heap[i] = self.heap[parent]
            i = parent

        self.heap[i] = item

    def pop(self):
        if not self.heap:
            raise IndexError("Heap is empty")

        result = self.heap[0]
        last = self.heap.pop()

        if not self.heap:
            return result

        i = 0
        n = len(self.heap)

        while 2 * i + 1 < n:
            left = 2 * i + 1
            right = left + 1
            smallest = left

            if (
                right < n
                and self.heap[right][:2] < self.heap[left][:2]
            ):
                smallest = right

            if last[:2] <= self.heap[smallest][:2]:
                break

            self.heap[i] = self.heap[smallest]
            i = smallest

        self.heap[i] = last
        return result

    def __len__(self):
        return len(self.heap)

class HuffmanNode:
    def __init__(self, character=None, left=None, right=None):
        self.character = character
        self.left = left
        self.right = right


def build_huffman_codes(text):
    if not isinstance(text, str):
        raise TypeError("Text must be a string")

    if not text:
        return {}

    frequencies = {}

    for char in text:
        frequencies[char] = frequencies.get(char, 0) + 1

    heap = MinHeap()
    tie_breaker = 0

    # Create one leaf for every distinct character.
    for char in sorted(frequencies):
        node = HuffmanNode(character=char)
        heap.push((frequencies[char], tie_breaker, node))
        tie_breaker += 1

    # Repeatedly combine the two least frequent nodes.
    while len(heap) > 1:
        freq1, _, left = heap.pop()
        freq2, _, right = heap.pop()

        parent = HuffmanNode(left=left, right=right)

        heap.push((
            freq1 + freq2,
            tie_breaker,
            parent
        ))
        tie_breaker += 1

    root = heap.pop()[2]
    codes = {}

    def traverse(node, code):
        if node.character is not None:
            codes[node.character] = code or "0"
            return

        traverse(node.left, code + "0")
        traverse(node.right, code + "1")

    traverse(root, "")
    return codes

def huffman_encode(text):
    codes = build_huffman_codes(text)

    encoded = "".join(
        codes[char] for char in text
    )

    return encoded, codes


def huffman_decode(bits, codes):
    if not isinstance(bits, str):
        raise TypeError("Encoded data must be a string")

    if not isinstance(codes, dict):
        raise TypeError("Codes must be a dictionary")

    if not codes:
        if bits:
            raise ValueError("Cannot decode without codes")
        return ""

    # Reconstruct a decoding tree.
    root = {}

    for char, code in codes.items():
        if not code or any(bit not in "01" for bit in code):
            raise ValueError("Invalid Huffman code")

        node = root

        for bit in code:
            if "_symbol" in node:
                raise ValueError("Codes are not prefix-free")

            node = node.setdefault(bit, {})

        if node:
            raise ValueError("Duplicate or non-prefix-free code")

        node["_symbol"] = char

    decoded = []
    node = root

    for bit in bits:
        if bit not in node:
            raise ValueError("Invalid encoded bit sequence")

        node = node[bit]

        if "_symbol" in node:
            decoded.append(node["_symbol"])
            node = root

    if node is not root:
        raise ValueError("Incomplete encoded bit sequence")

    return "".join(decoded)

RADIO_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"


def fixed_length_encode(text):
    if not isinstance(text, str):
        raise TypeError("Text must be a string")

    width = (len(RADIO_ALPHABET) - 1).bit_length()

    codes = {}

    for index, char in enumerate(RADIO_ALPHABET):
        codes[char] = format(index, f"0{width}b")

    encoded = []

    for char in text:
        if char not in codes:
            raise ValueError("Invalid radio log character")

        encoded.append(codes[char])

    return "".join(encoded), codes