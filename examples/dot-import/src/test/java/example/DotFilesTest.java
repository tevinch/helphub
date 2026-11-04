package example;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.eclipse.elk.graph.ElkNode;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class DotFilesTest {
    // This test fails if the external path is mishandled, conversion is skipped,
    // node/edge identity or text is lost, or the input is rewritten.
    @Test void importsExternalDotWithSpacesIntoRealElkGraph() throws Exception {
        Path path = Path.of("fixtures", "external graph.dot");
        byte[] before = Files.readAllBytes(path);
        List<ElkNode> roots = read(path);
        assertEquals(1, roots.size());
        ElkNode root = roots.get(0);
        assertEquals(2, root.getChildren().size());
        ElkNode source = root.getChildren().stream().filter(n -> "Café".equals(n.getLabels().get(0).getText())).findFirst().orElseThrow();
        ElkNode target = root.getChildren().stream().filter(n -> "Result".equals(n.getLabels().get(0).getText())).findFirst().orElseThrow();
        assertEquals("Café", source.getLabels().get(0).getText());
        assertEquals("Result", target.getLabels().get(0).getText());
        assertEquals(1, root.getContainedEdges().size());
        var edge = root.getContainedEdges().get(0);
        assertSame(source, edge.getSources().get(0));
        assertSame(target, edge.getTargets().get(0));
        assertEquals("go", edge.getLabels().get(0).getText());
        assertArrayEquals(before, Files.readAllBytes(path));
    }

    @Test void importsEveryTopLevelGraph() throws Exception {
        List<ElkNode> roots = read(Path.of("fixtures", "multiple graphs.dot"));
        assertEquals(2, roots.size());
        assertEquals(2, roots.get(0).getChildren().size());
        assertEquals(2, roots.get(1).getChildren().size());
        for (ElkNode root : roots) assertEquals(1, root.getContainedEdges().size());
    }

    @Test void rejectsMalformedDotBeforePartialConversion() {
        IOException error = assertThrows(IOException.class, () -> read(Path.of("fixtures", "malformed.dot")));
        assertTrue(error.getMessage().contains("DOT parse errors"), error.getMessage());
    }

    @Test void readsSuccessiveFilesIndependently() throws Exception {
        List<ElkNode> first = read(Path.of("fixtures", "external graph.dot"));
        List<ElkNode> second = read(Path.of("fixtures", "multiple graphs.dot"));
        assertEquals(1, first.size());
        assertEquals(2, second.size());
        assertEquals("Café", first.get(0).getChildren().get(0).getLabels().get(0).getText());
        assertNotSame(first.get(0), second.get(0));
    }

    @Test void missingFileIsAnIoFailure() {
        assertThrows(IOException.class, () -> read(Path.of("fixtures", "does not exist.dot")));
    }

    @Test void containsClusterPortEdgeInItsCommonAncestor() throws Exception {
        ElkNode root = read(Path.of("fixtures", "cluster and port.dot")).get(0);
        var cluster = root.getChildren().stream().filter(n -> !n.getChildren().isEmpty()).findFirst().orElseThrow();
        var inside = cluster.getChildren().get(0);
        var outside = root.getChildren().stream().filter(n -> !n.getLabels().isEmpty()).findFirst().orElseThrow();
        assertEquals("Inside", inside.getLabels().get(0).getText());
        assertEquals(1, root.getContainedEdges().size());
        var edge = root.getContainedEdges().get(0);
        assertSame(inside.getPorts().get(0), edge.getSources().get(0));
        assertSame(outside, edge.getTargets().get(0));
        assertSame(root, edge.getContainingNode());
        assertEquals("across", edge.getLabels().get(0).getText());
    }

    @Test void retainsNativeConversionMessages() throws Exception {
        List<String> messages = DotFiles.read(Path.of("fixtures", "conversion warning.dot")).messages();
        assertTrue(messages.stream().anyMatch(m -> m.contains("width") && m.contains("could not be parsed")), messages.toString());
        assertEquals(1, read(Path.of("fixtures", "conversion warning.dot")).get(0).getChildren().size());
    }

    private static List<ElkNode> read(Path path) throws IOException {
        return DotFiles.read(path).graphs();
    }
}
