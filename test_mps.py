#!/usr/bin/env python3
"""
Test script to verify MPS (Metal Performance Shaders) GPU support on Apple Silicon.
This checks if Whisper can use your M1 Max GPU for acceleration.
"""

import sys

print("=" * 60)
print("Testing MPS (Apple Silicon GPU) Support for Whisper")
print("=" * 60)

# Check PyTorch availability
try:
    import torch
    print(f"✅ PyTorch installed: v{torch.__version__}")
except ImportError:
    print("❌ PyTorch not installed")
    print("   Install with: pip install torch")
    sys.exit(1)

# Check MPS availability
if hasattr(torch.backends, 'mps'):
    print(f"✅ MPS backend is available")
    
    if torch.backends.mps.is_available():
        print(f"✅ MPS is available and can be used")
        
        # Try to create a tensor on MPS
        try:
            device = torch.device("mps")
            test_tensor = torch.randn(10, 10).to(device)
            print(f"✅ Successfully created tensor on MPS device")
            print(f"   Device: {test_tensor.device}")
        except Exception as e:
            print(f"⚠️  MPS available but couldn't create tensor: {e}")
    else:
        print(f"⚠️  MPS backend exists but is not available")
        print(f"   You may need macOS 12.3+ or PyTorch 2.0+")
else:
    print(f"❌ MPS backend not found in PyTorch")
    print(f"   You may need to upgrade PyTorch: pip install --upgrade torch")

print()

# Check Whisper
try:
    import whisper
    print(f"✅ Whisper installed: v{whisper.__version__}")
except ImportError:
    print("❌ Whisper not installed")
    print("   Install with: pip install openai-whisper")

print()
print("=" * 60)
print("Summary:")
print("=" * 60)

if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    print("✅ Your M1 Max can use GPU acceleration with --device mps")
    print("   Expected speedup: 3-10x faster than CPU")
else:
    print("⚠️  MPS not available. Whisper will fall back to CPU.")
    print("   Update PyTorch: pip install --upgrade torch")

print("=" * 60)
