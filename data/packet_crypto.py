from __future__ import annotations

import struct
from typing import Final

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESCCM
    from cryptography.exceptions import InvalidTag
except ImportError:
    AESCCM = None  # type: ignore[assignment, misc]
    InvalidTag = Exception  # type: ignore[assignment, misc]


class CryptoError(Exception):
    """Base exception for packet cryptography errors."""
    pass


class CryptoAuthenticationError(CryptoError):
    """Raised when authentication tag verification fails (integrity violated / tampered)."""
    pass


class PacketCrypto:
    """
    Lightweight packet cryptographic manager using AES-128-CCM with an 8-byte tag.
    
    Properties:
      - Authenticated Encryption with Associated Data (AEAD) standardized by NIST SP 800-38C.
      - 128-bit key (16 bytes).
      - 8-byte authentication tag (balance between communication overhead and security).
      - 13-byte deterministic Nonce reconstructed by Sink from (source_id, sequence_number).
      - Zero per-packet Nonce transmission overhead.
      - Fully pickle-safe for checkpoint preservation.
    """

    DEFAULT_TAG_LENGTH: Final[int] = 8
    DEFAULT_KEY: Final[bytes] = b"WSN_LIGHT_KEY16B"  # 16 bytes for AES-128

    def __init__(
        self,
        key: bytes | None = None,
        tag_length: int = DEFAULT_TAG_LENGTH
    ):
        if AESCCM is None:
            raise ImportError(
                "Thư viện 'cryptography' chưa được cài đặt. "
                "Vui lòng chạy: pip install cryptography"
            )

        self._tag_length = tag_length

        if key is None:
            self._key = self.DEFAULT_KEY
        else:
            if len(key) not in (16, 24, 32):
                raise ValueError(
                    f"Độ dài khóa không hợp lệ ({len(key)} bytes). "
                    f"AES-128 yêu cầu 16 bytes."
                )
            self._key = bytes(key)

        self._cipher = AESCCM(self._key, tag_length=self._tag_length)

    @property
    def key(self) -> bytes:
        return self._key

    @property
    def tag_length(self) -> int:
        return self._tag_length

    @staticmethod
    def build_nonce(source_id: int, sequence_number: int) -> bytes:
        """
        Builds a 13-byte unique nonce from source_id and sequence_number.
        Format:
          - source_id: 4 bytes (uint32, big-endian)
          - sequence_number: 8 bytes (uint64, big-endian)
          - flag: 1 byte (0x00)
        Total: 13 bytes.
        """
        return struct.pack(">IQB", source_id & 0xFFFFFFFF, sequence_number & 0xFFFFFFFFFFFFFFFF, 0)

    def encrypt_bytes(
        self,
        source_id: int,
        sequence_number: int,
        data: bytes,
        associated_data: bytes | None = None
    ) -> bytes:
        """
        Encrypts arbitrary bytes using AES-128-CCM with an 8-byte authentication tag.
        Resulting ciphertext length = len(data) + 8.
        """
        nonce = self.build_nonce(source_id, sequence_number)
        return self._cipher.encrypt(nonce, data, associated_data)

    def decrypt_bytes(
        self,
        source_id: int,
        sequence_number: int,
        ciphertext: bytes,
        associated_data: bytes | None = None
    ) -> bytes:
        """
        Decrypts ciphertext and verifies the 8-byte authentication tag.
        Raises CryptoAuthenticationError if tag verification fails.
        """
        nonce = self.build_nonce(source_id, sequence_number)
        try:
            return self._cipher.decrypt(nonce, ciphertext, associated_data)
        except InvalidTag as exc:
            raise CryptoAuthenticationError(
                f"Xác thực gói tin thất bại từ Sensor {source_id} (seq {sequence_number}). "
                "Dữ liệu có thể đã bị thay đổi hoặc sai khóa/nonce."
            ) from exc

    def encrypt_float32(
        self,
        source_id: int,
        sequence_number: int,
        value: float,
        associated_data: bytes | None = None
    ) -> bytes:
        """
        Convenience method to encrypt a single 4-byte float32 measurement.
        Output length: 4 (value) + 8 (tag) = 12 bytes.
        """
        payload = struct.pack(">f", float(value))
        return self.encrypt_bytes(source_id, sequence_number, payload, associated_data)

    def decrypt_float32(
        self,
        source_id: int,
        sequence_number: int,
        ciphertext: bytes,
        associated_data: bytes | None = None
    ) -> float:
        """
        Convenience method to decrypt a single 4-byte float32 measurement.
        """
        plaintext = self.decrypt_bytes(source_id, sequence_number, ciphertext, associated_data)
        if len(plaintext) != 4:
            raise ValueError(
                f"Độ dài plaintext ({len(plaintext)} bytes) không khớp với float32 (4 bytes)."
            )
        return struct.unpack(">f", plaintext)[0]

    # -------------------------------------------------------------
    # Pickle serialization support for Checkpoints
    # -------------------------------------------------------------
    def __getstate__(self) -> dict:
        return {
            "key": self._key,
            "tag_length": self._tag_length
        }

    def __setstate__(self, state: dict) -> None:
        self._key = state["key"]
        self._tag_length = state.get("tag_length", self.DEFAULT_TAG_LENGTH)
        self._cipher = AESCCM(self._key, tag_length=self._tag_length)
