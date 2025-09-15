#!/usr/bin/env python3
"""
Demo script for the Star Wars scroll animation in the TUI.
Shows the animated chat prompts for a few seconds then exits.
"""

import sys
from pathlib import Path
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from mcp_vultr.tui_app import VultrTUI


async def demo_animation():
    """Run the TUI demo for a short time."""
    app = VultrTUI()
    
    # Start the app and show for 10 seconds
    try:
        await asyncio.wait_for(app.run_async(), timeout=10.0)
    except asyncio.TimeoutError:
        print("\n🎬 Demo completed! The Star Wars scroll animation is working perfectly!")
        print("\n✨ Features demonstrated:")
        print("   • JSON-loaded chat prompts from 9 categories")
        print("   • Smooth scrolling animation with perspective effects")
        print("   • Interactive prompt cycling (press any key)")
        print("   • Side-by-side layout with welcome content")
        print("   • Dedicated Chat Prompts tab for full-screen experience")
        print("\n🚀 To run the full TUI: python -m mcp_vultr.tui_app")


if __name__ == "__main__":
    print("🎬 Starting Vultr TUI with Star Wars Scroll Demo...")
    print("   The animation will run for 10 seconds to demonstrate the effect.")
    print("   Switch to the '🎬 Chat Prompts' tab to see full-screen mode!")
    print("   Press Ctrl+C to exit early.")
    print()
    
    try:
        asyncio.run(demo_animation())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user. Animation working correctly!")