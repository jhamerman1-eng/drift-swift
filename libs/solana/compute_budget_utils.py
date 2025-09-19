"""
Solana Compute Budget Utilities

This module provides utilities for working with Solana compute budget instructions,
which are critical for optimizing transaction costs and ensuring reliable execution
on the Solana blockchain.

Key Features:
- Instruction type detection for compute budget management
- Transaction optimization helpers
- Cost calculation utilities
"""

from typing import Any, Dict, Optional
import base64
from dataclasses import dataclass
from enum import Enum

class ComputeBudgetInstructionType(Enum):
    """Types of compute budget instructions"""
    SET_COMPUTE_UNIT_LIMIT = "set_compute_unit_limit"
    SET_COMPUTE_UNIT_PRICE = "set_compute_unit_price" 
    REQUEST_HEAP_FRAME = "request_heap_frame"
    UNKNOWN = "unknown"

@dataclass
class ComputeBudgetInstruction:
    """Represents a Solana compute budget instruction"""
    instruction_type: ComputeBudgetInstructionType
    program_id: str
    data: bytes
    accounts: list
    
class ComputeBudgetProgram:
    """
    Python equivalent of Solana's ComputeBudgetProgram
    
    Provides methods to create compute budget instructions for transaction optimization.
    """
    
    # Solana Compute Budget Program ID
    PROGRAM_ID = "ComputeBudget111111111111111111111111111111"
    
    # Instruction discriminators (first byte of instruction data)
    SET_COMPUTE_UNIT_LIMIT_DISCRIMINATOR = 2
    SET_COMPUTE_UNIT_PRICE_DISCRIMINATOR = 3
    REQUEST_HEAP_FRAME_DISCRIMINATOR = 1
    
    @classmethod
    def set_compute_unit_limit(cls, units: int) -> ComputeBudgetInstruction:
        """
        Create an instruction to set the compute unit limit for a transaction.
        
        Args:
            units: Number of compute units to allocate (max 1,400,000)
            
        Returns:
            ComputeBudgetInstruction for setting compute unit limit
        """
        if units > 1_400_000:
            raise ValueError("Compute unit limit cannot exceed 1,400,000")
            
        # Instruction data: discriminator (1 byte) + units (4 bytes little-endian)
        data = bytes([cls.SET_COMPUTE_UNIT_LIMIT_DISCRIMINATOR]) + units.to_bytes(4, 'little')
        
        return ComputeBudgetInstruction(
            instruction_type=ComputeBudgetInstructionType.SET_COMPUTE_UNIT_LIMIT,
            program_id=cls.PROGRAM_ID,
            data=data,
            accounts=[]
        )
    
    @classmethod 
    def set_compute_unit_price(cls, micro_lamports: int) -> ComputeBudgetInstruction:
        """
        Create an instruction to set the compute unit price for a transaction.
        
        Args:
            micro_lamports: Price per compute unit in micro-lamports
            
        Returns:
            ComputeBudgetInstruction for setting compute unit price
        """
        # Instruction data: discriminator (1 byte) + micro_lamports (8 bytes little-endian)
        data = bytes([cls.SET_COMPUTE_UNIT_PRICE_DISCRIMINATOR]) + micro_lamports.to_bytes(8, 'little')
        
        return ComputeBudgetInstruction(
            instruction_type=ComputeBudgetInstructionType.SET_COMPUTE_UNIT_PRICE,
            program_id=cls.PROGRAM_ID,
            data=data,
            accounts=[]
        )
    
    @classmethod
    def request_heap_frame(cls, bytes_requested: int) -> ComputeBudgetInstruction:
        """
        Create an instruction to request additional heap memory.
        
        Args:
            bytes_requested: Number of additional heap bytes to request
            
        Returns:
            ComputeBudgetInstruction for requesting heap frame
        """
        data = bytes([cls.REQUEST_HEAP_FRAME_DISCRIMINATOR]) + bytes_requested.to_bytes(4, 'little')
        
        return ComputeBudgetInstruction(
            instruction_type=ComputeBudgetInstructionType.REQUEST_HEAP_FRAME,
            program_id=cls.PROGRAM_ID,
            data=data,
            accounts=[]
        )

def is_set_compute_units_ix(instruction: ComputeBudgetInstruction) -> bool:
    """
    Check if an instruction is a 'set compute unit limit' instruction.
    
    This utility function distinguishes between compute unit limit instructions
    and other compute budget instructions like compute unit price.
    
    Args:
        instruction: The instruction to check
        
    Returns:
        True if instruction sets compute unit limit, False otherwise
    """
    if instruction.program_id != ComputeBudgetProgram.PROGRAM_ID:
        return False
        
    return instruction.instruction_type == ComputeBudgetInstructionType.SET_COMPUTE_UNIT_LIMIT

def is_set_compute_price_ix(instruction: ComputeBudgetInstruction) -> bool:
    """
    Check if an instruction is a 'set compute unit price' instruction.
    
    Args:
        instruction: The instruction to check
        
    Returns:
        True if instruction sets compute unit price, False otherwise
    """
    if instruction.program_id != ComputeBudgetProgram.PROGRAM_ID:
        return False
        
    return instruction.instruction_type == ComputeBudgetInstructionType.SET_COMPUTE_UNIT_PRICE

def is_compute_budget_instruction(instruction: ComputeBudgetInstruction) -> bool:
    """
    Check if an instruction is any type of compute budget instruction.
    
    Args:
        instruction: The instruction to check
        
    Returns:
        True if instruction is a compute budget instruction, False otherwise
    """
    return instruction.program_id == ComputeBudgetProgram.PROGRAM_ID

def get_compute_unit_limit_from_instruction(instruction: ComputeBudgetInstruction) -> Optional[int]:
    """
    Extract the compute unit limit value from a set compute unit limit instruction.
    
    Args:
        instruction: The instruction to extract from
        
    Returns:
        The compute unit limit value, or None if not a valid instruction
    """
    if not is_set_compute_units_ix(instruction):
        return None
        
    if len(instruction.data) < 5:  # discriminator + 4 bytes for units
        return None
        
    # Extract units from bytes 1-4 (little-endian)
    return int.from_bytes(instruction.data[1:5], 'little')

def get_compute_unit_price_from_instruction(instruction: ComputeBudgetInstruction) -> Optional[int]:
    """
    Extract the compute unit price value from a set compute unit price instruction.
    
    Args:
        instruction: The instruction to extract from
        
    Returns:
        The compute unit price in micro-lamports, or None if not a valid instruction
    """
    if not is_set_compute_price_ix(instruction):
        return None
        
    if len(instruction.data) < 9:  # discriminator + 8 bytes for micro_lamports
        return None
        
    # Extract micro_lamports from bytes 1-8 (little-endian)
    return int.from_bytes(instruction.data[1:9], 'little')

def calculate_transaction_cost(
    compute_units: int, 
    compute_unit_price_micro_lamports: int
) -> int:
    """
    Calculate the total cost of a transaction in lamports.
    
    Args:
        compute_units: Number of compute units used
        compute_unit_price_micro_lamports: Price per compute unit in micro-lamports
        
    Returns:
        Total transaction cost in lamports
    """
    return (compute_units * compute_unit_price_micro_lamports) // 1_000_000

class ComputeBudgetOptimizer:
    """
    Helper class for optimizing compute budget settings in transactions.
    """
    
    # Recommended compute unit limits for different operation types
    OPERATION_COMPUTE_LIMITS = {
        'simple_transfer': 200_000,
        'token_transfer': 300_000,
        'swap': 500_000,
        'dex_trade': 800_000,
        'complex_defi': 1_200_000,
        'max_limit': 1_400_000
    }
    
    @classmethod
    def get_recommended_compute_limit(cls, operation_type: str) -> int:
        """
        Get recommended compute unit limit for an operation type.
        
        Args:
            operation_type: Type of operation being performed
            
        Returns:
            Recommended compute unit limit
        """
        return cls.OPERATION_COMPUTE_LIMITS.get(operation_type, cls.OPERATION_COMPUTE_LIMITS['max_limit'])
    
    @classmethod
    def calculate_optimal_price(
        cls, 
        priority_level: str = 'medium',
        base_fee_micro_lamports: int = 5000
    ) -> int:
        """
        Calculate optimal compute unit price based on priority level.
        
        Args:
            priority_level: 'low', 'medium', 'high', or 'critical'
            base_fee_micro_lamports: Base fee in micro-lamports
            
        Returns:
            Optimal compute unit price in micro-lamports
        """
        multipliers = {
            'low': 1.0,
            'medium': 1.5,
            'high': 2.0,
            'critical': 3.0
        }
        
        multiplier = multipliers.get(priority_level, 1.5)
        return int(base_fee_micro_lamports * multiplier)


