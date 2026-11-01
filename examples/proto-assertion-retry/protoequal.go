package protoassert

import (
	"fmt"

	"github.com/google/go-cmp/cmp"
	"github.com/stretchr/testify/assert"
	"google.golang.org/protobuf/testing/protocmp"
)

// HelperT is the subset used by AssertProtoEqual. Both testing.T and
// assert.CollectT satisfy it; full testing.TB is unnecessary here.
type HelperT interface {
	assert.TestingT
	Helper()
}

// AssertProtoEqual reports a semantic protobuf diff through its supplied test
// target. During EventuallyWithT, pass the callback's CollectT, not the outer T.
func AssertProtoEqual(t HelperT, want, got any, msgAndArgs ...any) {
	t.Helper()
	if diff := cmp.Diff(want, got, protocmp.Transform()); diff != "" {
		assert.Fail(t, fmt.Sprintf("not equal (-want +got):\n%s", diff), msgAndArgs...)
	}
}
