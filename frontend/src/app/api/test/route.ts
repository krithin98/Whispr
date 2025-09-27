import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const response = await fetch('http://localhost:8000/strategies');
    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }
    const strategies = await response.json();
    return NextResponse.json({ 
      success: true, 
      message: 'Backend connection successful',
      strategyCount: Array.isArray(strategies) ? strategies.length : 0
    });
  } catch (error) {
    return NextResponse.json({ 
      success: false, 
      message: 'Backend connection failed',
      error: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
} 