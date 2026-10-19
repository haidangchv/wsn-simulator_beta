import pickle
import unittest
import numpy as np

from data.packet_crypto import (
    PacketCrypto,
    CryptoAuthenticationError
)
from core.network import WirelessSensorNetwork
from core.sensor import SensorNode
from core.sink import SinkNode
from simulation.simulator import WSNSimulator


class TestPacketCrypto(unittest.TestCase):
    """
    Test suite for Lightweight Packet Encryption (AES-128-CCM-8).
    Includes 5 independent unit tests:
      1. Float32 encryption and decryption roundtrip.
      2. Integrity verification & tamper detection.
      3. Nonce uniqueness and collision prevention.
      4. Pickle serialization and state restoration for checkpoints.
      5. End-to-end integration with WSNSimulator.
    """

    def setUp(self):
        self.crypto = PacketCrypto()

    def test_encryption_decryption_float32(self):
        """
        1. Test standard encryption and decryption of float32 values.
        """
        source_id = 15
        seq_num = 1
        original_value = 31.73

        ciphertext = self.crypto.encrypt_float32(
            source_id=source_id,
            sequence_number=seq_num,
            value=original_value
        )

        # 4 bytes value + 8 bytes tag = 12 bytes total
        self.assertEqual(len(ciphertext), 12)

        decrypted_value = self.crypto.decrypt_float32(
            source_id=source_id,
            sequence_number=seq_num,
            ciphertext=ciphertext
        )

        self.assertAlmostEqual(decrypted_value, original_value, places=3)

    def test_tamper_detection(self):
        """
        2. Test that modifying even 1 bit in ciphertext or tag triggers CryptoAuthenticationError.
        """
        source_id = 42
        seq_num = 100
        val = 24.5

        ciphertext = self.crypto.encrypt_float32(
            source_id=source_id,
            sequence_number=seq_num,
            value=val
        )

        # Tamper payload
        tampered_bytes = bytearray(ciphertext)
        tampered_bytes[0] ^= 0x01

        with self.assertRaises(CryptoAuthenticationError):
            self.crypto.decrypt_float32(
                source_id=source_id,
                sequence_number=seq_num,
                ciphertext=bytes(tampered_bytes)
            )

        # Tamper tag (last byte)
        tampered_tag = bytearray(ciphertext)
        tampered_tag[-1] ^= 0x80

        with self.assertRaises(CryptoAuthenticationError):
            self.crypto.decrypt_float32(
                source_id=source_id,
                sequence_number=seq_num,
                ciphertext=bytes(tampered_tag)
            )

        # Mismatched sequence number (replay or desync attack)
        with self.assertRaises(CryptoAuthenticationError):
            self.crypto.decrypt_float32(
                source_id=source_id,
                sequence_number=seq_num + 1,  # Wrong seq num
                ciphertext=ciphertext
            )

    def test_nonce_uniqueness(self):
        """
        3. Test nonce uniqueness across different sensors and sequential packets.
        """
        seen_nonces = set()

        for sid in range(10):
            for seq in range(100):
                nonce = PacketCrypto.build_nonce(sid, seq)
                self.assertEqual(len(nonce), 13)
                self.assertNotIn(nonce, seen_nonces)
                seen_nonces.add(nonce)

        self.assertEqual(len(seen_nonces), 1000)

    def test_checkpoint_serialization(self):
        """
        4. Test pickle serialization and state restoration for Checkpoints.
        """
        key = b"TEST_SECRET_KEY1"
        crypto_inst = PacketCrypto(key=key, tag_length=8)

        # Encrypt packet
        encrypted = crypto_inst.encrypt_float32(
            source_id=7,
            sequence_number=55,
            value=99.125
        )

        # Pickle & restore
        pickled_data = pickle.dumps(crypto_inst)
        restored_crypto: PacketCrypto = pickle.loads(pickled_data)

        self.assertEqual(restored_crypto.key, key)
        self.assertEqual(restored_crypto.tag_length, 8)

        # Decrypt using restored instance
        recovered_val = restored_crypto.decrypt_float32(
            source_id=7,
            sequence_number=55,
            ciphertext=encrypted
        )
        self.assertAlmostEqual(recovered_val, 99.125, places=3)

    def test_simulator_crypto_integration(self):
        """
        5. Test WSNSimulator end-to-end with packet_crypto enabled.
        """
        # Minimal network setup
        sensors = [
            SensorNode(
                node_id=1,
                x=100.0,
                y=100.0,
                sensor_type="temperature",
                initial_energy=20.0,
                remaining_energy=20.0,
                transmission_range=300.0
            ),
            SensorNode(
                node_id=2,
                x=200.0,
                y=100.0,
                sensor_type="temperature",
                initial_energy=20.0,
                remaining_energy=20.0,
                transmission_range=300.0
            )
        ]

        sink = SinkNode(node_id="SINK", x=300.0, y=100.0)
        net = WirelessSensorNetwork(sensors=sensors, sink=sink)
        net.build_topology()

        config = {
            "network": {"width_m": 500, "height_m": 500, "num_sensors": 2, "random_seed": 42},
            "sink": {"x": 300, "y": 100},
            "energy": {
                "e_elec_nj_per_bit": 50,
                "eps_fs_pj_per_bit_m2": 10,
                "eps_mp_pj_per_bit_m4": 0.0013,
                "per_hop_delay_ms": 10
            },
            "radio": {
                "data_rate_bps": 250000,
                "processing_delay_ms_per_hop": 1.0,
                "propagation_speed_m_s": 300000000
            },
            "sensor": {
                "initial_energy_j": 20.0,
                "transmission_range_m": 300,
                "energy_threshold_ratio": 0.15
            },
            "packet": {
                "payload_size_bytes": 64,
                "sampling_interval_seconds": 3600
            },
            "simulation": {
                "mode": "round_based",
                "max_rounds": 10,
                "time": {
                    "start_datetime": "2026-01-01 00:00:00",
                    "round_duration_minutes": 60
                }
            },
            "routing": {
                "algorithm": "minimum_hop",
                "energy_threshold_ratio": 0.15
            },
            "environment": {"enabled": False},
            "packet_crypto": {
                "enabled": True,
                "algorithm": "aes_ccm_128",
                "tag_bytes": 8,
                "header_bytes": 12,
                "cpu_energy_nj_per_byte": 1.2
            }
        }

        sim = WSNSimulator(network=net, config=config)
        self.assertTrue(sim.crypto_enabled)
        self.assertIsNotNone(sim.packet_crypto)

        # Run 1 round
        sim.run_round()

        metrics = sim.get_metrics()
        self.assertTrue(metrics["crypto_enabled"])
        self.assertGreater(metrics["crypto_encrypted_packets"], 0)
        self.assertEqual(metrics["crypto_decrypted_packets"], metrics["crypto_encrypted_packets"])
        self.assertEqual(metrics["crypto_auth_failures"], 0)
        self.assertEqual(metrics["crypto_total_overhead_bytes"], metrics["crypto_encrypted_packets"] * 8)

        # Test Checkpoint Save & Restore with Crypto
        from simulation.checkpoint import (
            create_checkpoint_bytes,
            restore_checkpoint_bytes
        )

        chk_bytes = create_checkpoint_bytes(sim, config)
        restored = restore_checkpoint_bytes(chk_bytes)
        restored_sim: WSNSimulator = restored["simulator"]

        self.assertTrue(restored_sim.crypto_enabled)
        self.assertIsNotNone(restored_sim.packet_crypto)

        # Run next round on restored simulator
        restored_sim.run_round()
        restored_metrics = restored_sim.get_metrics()
        self.assertEqual(restored_sim.current_round, 2)
        self.assertEqual(
            restored_metrics["crypto_decrypted_packets"],
            restored_metrics["crypto_encrypted_packets"]
        )
        self.assertEqual(restored_metrics["crypto_auth_failures"], 0)


if __name__ == "__main__":
    unittest.main()

