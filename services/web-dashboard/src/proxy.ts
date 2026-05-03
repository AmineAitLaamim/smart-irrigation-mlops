import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  if (
    request.nextUrl.pathname.startsWith('/v1/') ||
    request.nextUrl.pathname.startsWith('/users/') ||
    request.nextUrl.pathname.startsWith('/quality/')
  ) {
    const token = request.cookies.get('token')?.value;
    const requestHeaders = new Headers(request.headers);
    
    if (token) {
      requestHeaders.set('Authorization', `Bearer ${token}`);
    }

    // Proxy the request to the API Gateway
    const targetUrl = new URL(
      `${process.env.API_GATEWAY_URL}${request.nextUrl.pathname}${request.nextUrl.search}`
    );
    
    return NextResponse.rewrite(targetUrl, {
      request: {
        headers: requestHeaders,
      },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/v1/:path*', '/users/:path*', '/quality/:path*'],
};
