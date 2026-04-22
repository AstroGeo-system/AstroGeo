/**
 * Catch-all server-side proxy for the FastAPI backend.
 * Runs on the Netlify serverless edge — reads NEXT_PUBLIC_API_URL or API_URL
 * at REQUEST TIME (not build time), so no rebuild is needed when the env var changes.
 *
 * GET/POST /api/backend/:path* → proxied to BACKEND/:path*
 */

import { NextResponse } from 'next/server'

export const runtime = 'nodejs'

const BACKEND = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8000'

async function proxy(request, { params }) {
  const pathParts = (await params).path ?? []
  const targetPath = pathParts.join('/')
  const { search } = new URL(request.url)
  const targetUrl = `${BACKEND}/${targetPath}${search}`

  const headers = {
    'Content-Type': 'application/json',
  }

  try {
    const isGet = request.method === 'GET'
    const body = isGet ? undefined : await request.text()

    const res = await fetch(targetUrl, {
      method:  request.method,
      headers,
      body,
      cache:   'no-store',
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    console.error(`[Proxy] Failed ${request.method} ${targetUrl}:`, err.message)
    return NextResponse.json(
      { error: 'Backend unreachable', detail: err.message, target: targetUrl },
      { status: 503 }
    )
  }
}

export const GET  = proxy
export const POST = proxy
export const PUT  = proxy
export const DELETE = proxy
