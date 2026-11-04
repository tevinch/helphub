package example;

import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.eclipse.elk.alg.graphviz.dot.GraphvizDotStandaloneSetup;
import org.eclipse.elk.alg.graphviz.dot.dot.GraphvizModel;
import org.eclipse.elk.alg.graphviz.dot.transform.DotImporter;
import org.eclipse.elk.alg.graphviz.dot.transform.DotResourceSetProvider;
import org.eclipse.elk.alg.graphviz.dot.transform.DotTransformationData;
import org.eclipse.elk.graph.ElkNode;
import org.eclipse.elk.graph.util.ElkGraphUtil;
import org.eclipse.emf.common.util.URI;
import org.eclipse.xtext.resource.XtextResource;

/** Reads DOT files into native ELK graphs, without running a layout algorithm. */
public final class DotFiles {
    private DotFiles() { }

    public record ImportResult(List<ElkNode> graphs, List<String> messages) { }

    public static ImportResult read(Path path) throws IOException {
        var injector = new GraphvizDotStandaloneSetup().createInjectorAndDoEMFRegistration();
        var resources = injector.getInstance(DotResourceSetProvider.class).createResourceSet();
        // The language registers graphviz_dot. The input file can still be named *.dot.
        var resource = resources.createResource(URI.createURI("memory:/input.graphviz_dot"));
        try (InputStream input = Files.newInputStream(path)) {
            resource.load(input, Map.of(XtextResource.OPTION_ENCODING, "UTF-8"));
        }
        if (!resource.getErrors().isEmpty()) {
            String errors = resource.getErrors().stream()
                    .map(d -> "line " + d.getLine() + ": " + d.getMessage())
                    .collect(Collectors.joining("; "));
            throw new IOException("DOT parse errors: " + errors);
        }
        if (resource.getContents().size() != 1
                || !(resource.getContents().get(0) instanceof GraphvizModel model)) {
            throw new IOException("Expected a GraphvizModel root");
        }
        var data = new DotTransformationData<GraphvizModel, ElkNode>();
        data.setSourceGraph(model);
        new DotImporter().transform(data);
        // The importer connects edges but does not assign their containment.
        // Use ELK's public helper, including edges attached through ports.
        for (ElkNode root : data.getTargetGraphs()) {
            List<ElkNode> nodes = new ArrayList<>(List.of(root));
            for (int i = 0; i < nodes.size(); i++) {
                ElkNode node = nodes.get(i);
                nodes.addAll(node.getChildren());
                for (var edge : ElkGraphUtil.allOutgoingEdges(node)) {
                    ElkGraphUtil.updateContainment(edge);
                }
            }
        }
        List<String> messages = new ArrayList<>();
        data.getMessages().forEach(messages::add);
        return new ImportResult(List.copyOf(data.getTargetGraphs()), List.copyOf(messages));
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 1) throw new IllegalArgumentException("Usage: DotFiles <input.dot>");
        ImportResult result = read(Path.of(args[0]));
        var output = new PrintWriter(System.out, true, StandardCharsets.UTF_8);
        var errors = new PrintWriter(System.err, true, StandardCharsets.UTF_8);
        for (int g = 0; g < result.graphs().size(); g++) {
            ElkNode graph = result.graphs().get(g);
            output.printf("graph %d: %d nodes, %d edges%n",
                    g + 1, graph.getChildren().size(), graph.getContainedEdges().size());
            for (int n = 0; n < graph.getChildren().size(); n++) {
                var node = graph.getChildren().get(n);
                output.printf("  node %d: %s%n", n,
                        node.getLabels().stream().map(l -> l.getText()).collect(Collectors.joining(", ")));
            }
            for (var edge : graph.getContainedEdges()) {
                output.printf("  edge label: %s%n",
                        edge.getLabels().stream().map(l -> l.getText()).collect(Collectors.joining(", ")));
            }
        }
        result.messages().forEach(message -> errors.println("Import: " + message));
    }
}
