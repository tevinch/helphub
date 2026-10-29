package sharedheader

import (
	"context"

	"connectrpc.com/connect/v2"
)

// DefaultUserAgent shares an application default without replacing a call's header.
func DefaultUserAgent(value string) connect.ClientInterceptor {
	return func(next connect.ClientFunc) connect.ClientFunc {
		return func(ctx context.Context, spec connect.Spec) (connect.ClientStream, error) {
			info, _ := connect.CallInfoForClientContext(ctx)
			header := info.RequestHeader()
			if !header.Has("User-Agent") {
				header.Set("User-Agent", value)
			}
			return next(ctx, spec)
		}
	}
}
