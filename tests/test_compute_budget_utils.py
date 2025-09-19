"""
Unit tests for Solana compute budget utilities.

This module tests the compute budget instruction detection and optimization
utilities, ensuring proper transaction cost management and execution reliability.
"""

import pytest
from libs.solana.compute_budget_utils import (
    ComputeBudgetProgram,
    ComputeBudgetInstruction,
    ComputeBudgetInstructionType,
    is_set_compute_units_ix,
    is_set_compute_price_ix,
    is_compute_budget_instruction,
    get_compute_unit_limit_from_instruction,
    get_compute_unit_price_from_instruction,
    calculate_transaction_cost,
    ComputeBudgetOptimizer
)

class TestComputeBudgetInstructionDetection:
    """Test suite for compute budget instruction detection utilities"""
    
    def test_is_set_compute_units_ix(self):
        """Test detection of compute unit limit instructions"""
        # Create compute unit limit instruction
        cu_limit_ix = ComputeBudgetProgram.set_compute_unit_limit(units=1_400_000)
        
        # Create compute unit price instruction  
        cu_price_ix = ComputeBudgetProgram.set_compute_unit_price(micro_lamports=10_000)
        
        # Test the detection function (equivalent to the original TypeScript test)
        assert is_set_compute_units_ix(cu_limit_ix) == True
        assert is_set_compute_units_ix(cu_price_ix) == False
    
    def test_is_set_compute_price_ix(self):
        """Test detection of compute unit price instructions"""
        cu_limit_ix = ComputeBudgetProgram.set_compute_unit_limit(units=500_000)
        cu_price_ix = ComputeBudgetProgram.set_compute_unit_price(micro_lamports=5_000)
        
        assert is_set_compute_price_ix(cu_price_ix) == True
        assert is_set_compute_price_ix(cu_limit_ix) == False
    
    def test_is_compute_budget_instruction(self):
        """Test general compute budget instruction detection"""
        cu_limit_ix = ComputeBudgetProgram.set_compute_unit_limit(units=300_000)
        cu_price_ix = ComputeBudgetProgram.set_compute_unit_price(micro_lamports=7_500)
        heap_ix = ComputeBudgetProgram.request_heap_frame(bytes_requested=32_768)
        
        # All should be compute budget instructions
        assert is_compute_budget_instruction(cu_limit_ix) == True
        assert is_compute_budget_instruction(cu_price_ix) == True
        assert is_compute_budget_instruction(heap_ix) == True
        
        # Create a non-compute-budget instruction
        non_cb_ix = ComputeBudgetInstruction(
            instruction_type=ComputeBudgetInstructionType.UNKNOWN,
            program_id="SomeOtherProgram111111111111111111111111111",
            data=b"\x00\x01\x02",
            accounts=[]
        )
        
        assert is_compute_budget_instruction(non_cb_ix) == False

class TestComputeBudgetProgram:
    """Test suite for ComputeBudgetProgram instruction creation"""
    
    def test_set_compute_unit_limit_creation(self):
        """Test creation of compute unit limit instructions"""
        units = 800_000
        instruction = ComputeBudgetProgram.set_compute_unit_limit(units)
        
        assert instruction.instruction_type == ComputeBudgetInstructionType.SET_COMPUTE_UNIT_LIMIT
        assert instruction.program_id == ComputeBudgetProgram.PROGRAM_ID
        assert len(instruction.data) == 5  # 1 byte discriminator + 4 bytes units
        assert instruction.data[0] == ComputeBudgetProgram.SET_COMPUTE_UNIT_LIMIT_DISCRIMINATOR
        
        # Extract and verify the units value
        extracted_units = int.from_bytes(instruction.data[1:5], 'little')
        assert extracted_units == units
    
    def test_set_compute_unit_price_creation(self):
        """Test creation of compute unit price instructions"""
        micro_lamports = 15_000
        instruction = ComputeBudgetProgram.set_compute_unit_price(micro_lamports)
        
        assert instruction.instruction_type == ComputeBudgetInstructionType.SET_COMPUTE_UNIT_PRICE
        assert instruction.program_id == ComputeBudgetProgram.PROGRAM_ID
        assert len(instruction.data) == 9  # 1 byte discriminator + 8 bytes micro_lamports
        assert instruction.data[0] == ComputeBudgetProgram.SET_COMPUTE_UNIT_PRICE_DISCRIMINATOR
        
        # Extract and verify the micro_lamports value
        extracted_price = int.from_bytes(instruction.data[1:9], 'little')
        assert extracted_price == micro_lamports
    
    def test_compute_unit_limit_validation(self):
        """Test validation of compute unit limits"""
        # Valid limit
        ComputeBudgetProgram.set_compute_unit_limit(1_400_000)
        
        # Invalid limit (too high)
        with pytest.raises(ValueError, match="Compute unit limit cannot exceed 1,400,000"):
            ComputeBudgetProgram.set_compute_unit_limit(1_500_000)
    
    def test_request_heap_frame_creation(self):
        """Test creation of heap frame request instructions"""
        bytes_requested = 32_768
        instruction = ComputeBudgetProgram.request_heap_frame(bytes_requested)
        
        assert instruction.instruction_type == ComputeBudgetInstructionType.REQUEST_HEAP_FRAME
        assert instruction.program_id == ComputeBudgetProgram.PROGRAM_ID
        assert len(instruction.data) == 5  # 1 byte discriminator + 4 bytes
        assert instruction.data[0] == ComputeBudgetProgram.REQUEST_HEAP_FRAME_DISCRIMINATOR

class TestInstructionDataExtraction:
    """Test suite for extracting data from compute budget instructions"""
    
    def test_get_compute_unit_limit_from_instruction(self):
        """Test extraction of compute unit limit values"""
        units = 600_000
        instruction = ComputeBudgetProgram.set_compute_unit_limit(units)
        
        extracted_units = get_compute_unit_limit_from_instruction(instruction)
        assert extracted_units == units
        
        # Test with non-compute-unit instruction
        price_instruction = ComputeBudgetProgram.set_compute_unit_price(5_000)
        assert get_compute_unit_limit_from_instruction(price_instruction) is None
    
    def test_get_compute_unit_price_from_instruction(self):
        """Test extraction of compute unit price values"""
        micro_lamports = 12_500
        instruction = ComputeBudgetProgram.set_compute_unit_price(micro_lamports)
        
        extracted_price = get_compute_unit_price_from_instruction(instruction)
        assert extracted_price == micro_lamports
        
        # Test with non-compute-price instruction
        limit_instruction = ComputeBudgetProgram.set_compute_unit_limit(400_000)
        assert get_compute_unit_price_from_instruction(limit_instruction) is None

class TestTransactionCostCalculation:
    """Test suite for transaction cost calculations"""
    
    def test_calculate_transaction_cost(self):
        """Test transaction cost calculation"""
        # Test case 1: Basic calculation
        compute_units = 200_000
        price_micro_lamports = 10_000
        expected_cost = (200_000 * 10_000) // 1_000_000  # 2_000 lamports
        
        cost = calculate_transaction_cost(compute_units, price_micro_lamports)
        assert cost == expected_cost
        
        # Test case 2: High compute usage
        compute_units = 1_000_000
        price_micro_lamports = 25_000
        expected_cost = (1_000_000 * 25_000) // 1_000_000  # 25_000 lamports
        
        cost = calculate_transaction_cost(compute_units, price_micro_lamports)
        assert cost == expected_cost
        
        # Test case 3: Low usage (should handle fractional lamports)
        compute_units = 50_000
        price_micro_lamports = 5_000
        expected_cost = (50_000 * 5_000) // 1_000_000  # 250 lamports
        
        cost = calculate_transaction_cost(compute_units, price_micro_lamports)
        assert cost == expected_cost

class TestComputeBudgetOptimizer:
    """Test suite for compute budget optimization utilities"""
    
    def test_get_recommended_compute_limit(self):
        """Test recommended compute limit suggestions"""
        assert ComputeBudgetOptimizer.get_recommended_compute_limit('simple_transfer') == 200_000
        assert ComputeBudgetOptimizer.get_recommended_compute_limit('token_transfer') == 300_000
        assert ComputeBudgetOptimizer.get_recommended_compute_limit('swap') == 500_000
        assert ComputeBudgetOptimizer.get_recommended_compute_limit('dex_trade') == 800_000
        assert ComputeBudgetOptimizer.get_recommended_compute_limit('complex_defi') == 1_200_000
        
        # Test unknown operation type (should return max)
        assert ComputeBudgetOptimizer.get_recommended_compute_limit('unknown_operation') == 1_400_000
    
    def test_calculate_optimal_price(self):
        """Test optimal price calculation based on priority"""
        base_fee = 5_000
        
        # Test different priority levels
        low_price = ComputeBudgetOptimizer.calculate_optimal_price('low', base_fee)
        medium_price = ComputeBudgetOptimizer.calculate_optimal_price('medium', base_fee)
        high_price = ComputeBudgetOptimizer.calculate_optimal_price('high', base_fee)
        critical_price = ComputeBudgetOptimizer.calculate_optimal_price('critical', base_fee)
        
        assert low_price == 5_000      # 1.0x multiplier
        assert medium_price == 7_500   # 1.5x multiplier
        assert high_price == 10_000    # 2.0x multiplier
        assert critical_price == 15_000  # 3.0x multiplier
        
        # Test default priority (should be medium)
        default_price = ComputeBudgetOptimizer.calculate_optimal_price(base_fee_micro_lamports=base_fee)
        assert default_price == medium_price

class TestIntegrationScenarios:
    """Integration tests simulating real-world usage scenarios"""
    
    def test_swift_trading_optimization(self):
        """Test compute budget optimization for Swift trading scenarios"""
        # Scenario: High-frequency trading bot needs optimal settings
        
        # Create instructions for a DEX trade
        compute_limit = ComputeBudgetOptimizer.get_recommended_compute_limit('dex_trade')
        optimal_price = ComputeBudgetOptimizer.calculate_optimal_price('high')
        
        limit_ix = ComputeBudgetProgram.set_compute_unit_limit(compute_limit)
        price_ix = ComputeBudgetProgram.set_compute_unit_price(optimal_price)
        
        # Verify instructions are correctly identified
        assert is_set_compute_units_ix(limit_ix) == True
        assert is_set_compute_price_ix(price_ix) == True
        
        # Verify values can be extracted
        assert get_compute_unit_limit_from_instruction(limit_ix) == compute_limit
        assert get_compute_unit_price_from_instruction(price_ix) == optimal_price
        
        # Calculate expected transaction cost
        expected_cost = calculate_transaction_cost(compute_limit, optimal_price)
        assert expected_cost > 0  # Should have some cost
    
    def test_transaction_simulation_workflow(self):
        """Test the complete workflow from instruction creation to cost analysis"""
        # Simulate the workflow from the original TypeScript test
        
        # Create instructions (like the original test)
        cu_limit_ix = ComputeBudgetProgram.set_compute_unit_limit(units=1_400_000)
        cu_price_ix = ComputeBudgetProgram.set_compute_unit_price(micro_lamports=10_000)
        
        # Verify instruction types (main test from original)
        assert is_set_compute_units_ix(cu_limit_ix) == True
        assert is_set_compute_units_ix(cu_price_ix) == False
        
        # Extended analysis beyond original test
        instructions = [cu_limit_ix, cu_price_ix]
        
        # Analyze all instructions
        compute_limit = None
        compute_price = None
        
        for ix in instructions:
            if is_set_compute_units_ix(ix):
                compute_limit = get_compute_unit_limit_from_instruction(ix)
            elif is_set_compute_price_ix(ix):
                compute_price = get_compute_unit_price_from_instruction(ix)
        
        # Verify we found both values
        assert compute_limit == 1_400_000
        assert compute_price == 10_000
        
        # Calculate total transaction cost
        total_cost = calculate_transaction_cost(compute_limit, compute_price)
        assert total_cost == 14_000  # (1,400,000 * 10,000) / 1,000,000

# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])


