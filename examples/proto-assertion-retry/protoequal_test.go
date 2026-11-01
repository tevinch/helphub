package protoassert

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/structpb"
	"google.golang.org/protobuf/types/known/wrapperspb"
)

var _ HelperT = (*testing.T)(nil)
var _ HelperT = (*assert.CollectT)(nil)

func TestDirectProtoAssertion(t *testing.T) {
	want, err := structpb.NewStruct(map[string]any{
		"state": "ready", "nested": map[string]any{"attempt": 3.0},
	})
	if err != nil {
		t.Fatal(err)
	}
	AssertProtoEqual(t, want, proto.Clone(want), "direct assertion")
}

func TestProtoAssertionRetriesWithoutFailingOuterTest(t *testing.T) {
	var calls atomic.Int32
	ok := assert.EventuallyWithT(t, func(c *assert.CollectT) {
		attempt := calls.Add(1)
		state := "pending"
		if attempt >= 3 {
			state = "ready"
		}
		AssertProtoEqual(c, wrapperspb.String("ready"), wrapperspb.String(state), "readiness")
	}, 2*time.Second, time.Millisecond)
	if !ok || calls.Load() != 3 {
		t.Fatalf("expected successful third attempt, got success=%t calls=%d", ok, calls.Load())
	}
}

func TestTimeoutReportsFinalProtoDiff(t *testing.T) {
	binary, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(binary, "-test.run=^TestTimeoutChild$", "-test.v")
	cmd.Env = append(os.Environ(), "PROTO_TIMEOUT_CHILD=1")
	output, err := cmd.CombinedOutput()
	var exitError *exec.ExitError
	if !errors.As(err, &exitError) || exitError.ExitCode() != 1 {
		t.Fatalf("an always-unequal protobuf must fail the child test: %s", output)
	}
	text := string(output)
	for _, required := range []string{"Condition never satisfied", "not equal (-want +got)", "ready", "pending", "timeout readiness"} {
		if !strings.Contains(text, required) {
			t.Fatalf("child failure omitted %q: %s", required, text)
		}
	}
	if !regexp.MustCompile(`completed attempts: [1-9][0-9]*`).MatchString(text) {
		t.Fatalf("no independent evidence that the callback ran: %s", text)
	}
	if strings.Contains(text, "panic:") || strings.Contains(text, "DATA RACE") {
		t.Fatalf("timeout must be an assertion failure, not a crash/race: %s", text)
	}
	t.Log("child test failed with the final protobuf diff after real retry attempts")
}

func TestTimeoutChild(t *testing.T) {
	if os.Getenv("PROTO_TIMEOUT_CHILD") != "1" {
		t.Skip("intentional timeout failure runs in its own test process")
	}
	var calls atomic.Int32
	assert.EventuallyWithT(t, func(c *assert.CollectT) {
		calls.Add(1)
		AssertProtoEqual(c, wrapperspb.String("ready"), wrapperspb.String("pending"), "timeout readiness")
	}, 100*time.Millisecond, time.Millisecond)
	fmt.Printf("completed attempts: %d\n", calls.Load())
}

func TestOriginalAndOneMethodSignaturesDoNotCompile(t *testing.T) {
	for _, example := range []struct{ name, parameter, diagnostic string }{
		{"original TB", "testing.TB", "testing.TB"},
		{"Errorf only", "assert.TestingT", "t.Helper undefined"},
	} {
		t.Run(example.name, func(t *testing.T) {
			directory := t.TempDir()
			for _, name := range []string{"go.mod", "go.sum"} {
				data, err := os.ReadFile(name)
				if err != nil {
					t.Fatal(err)
				}
				if err := os.WriteFile(filepath.Join(directory, name), data, 0600); err != nil {
					t.Fatal(err)
				}
			}
			source := fmt.Sprintf(`package contrast
import (
 "fmt"
 "testing"
 "time"
 "github.com/google/go-cmp/cmp"
 "github.com/stretchr/testify/assert"
 "google.golang.org/protobuf/testing/protocmp"
 "google.golang.org/protobuf/types/known/wrapperspb"
)
func AssertProtoEqual(t %s, want, got any, msgAndArgs ...any) {
 t.Helper()
 if diff := cmp.Diff(want, got, protocmp.Transform()); diff != "" {
  assert.Fail(t, fmt.Sprintf("not equal (-want +got):\n%%s", diff), msgAndArgs...)
 }
}
func TestUse(t *testing.T) {
 assert.EventuallyWithT(t, func(c *assert.CollectT) {
  AssertProtoEqual(c, wrapperspb.String("ready"), wrapperspb.String("ready"))
 }, time.Second, time.Millisecond)
}
`, example.parameter)
			if err := os.WriteFile(filepath.Join(directory, "contrast_test.go"), []byte(source), 0600); err != nil {
				t.Fatal(err)
			}
			cmd := exec.Command("go", "test", "-mod=readonly", ".")
			cmd.Dir = directory
			cmd.Env = append(os.Environ(), "GOWORK=off")
			output, err := cmd.CombinedOutput()
			if err == nil || !strings.Contains(string(output), example.diagnostic) {
				t.Fatalf("expected %s compiler rejection, got error=%v output=%s", example.diagnostic, err, output)
			}
		})
	}
}
