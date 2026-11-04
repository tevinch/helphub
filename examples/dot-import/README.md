# Import Graphviz DOT in plain Java

This example reads an external UTF-8 `.dot` file into ELK graph objects using the published `org.eclipse.elk.alg.graphviz.dot` module. It uses ELK **0.12.1** without an Eclipse application, a running OSGi framework, or the Graphviz executable.

You need a JDK **17 or newer** and Maven. The example was checked with JDK **21.0.12.1** and Maven **3.10.0**, compiling Java 17 bytecode. It has not been run on a Java 17 runtime.

From this directory:

```sh
mvn clean test
mvn -q compile exec:java -Dexec.mainClass=example.DotFiles '-Dexec.args="fixtures/external graph.dot"'
```

The second command prints:

```text
graph 1: 2 nodes, 1 edges
  node 0: Café
  node 1: Result
  edge label: go
```

Replace the path inside `exec.args` with your file. Keep its double quotes when the path contains spaces. The file is read without being renamed or rewritten.

The Maven exec configuration lets the standalone JVM terminate EMF's background daemon thread normally; this avoids a shutdown interruption trace.

To use the result in your application:

```java
import example.DotFiles;
import java.nio.file.Path;
import org.eclipse.elk.graph.ElkNode;

// Inside your application method:
var result = DotFiles.read(Path.of("my graph.dot"));
for (ElkNode graph : result.graphs()) {
    // Use the native ELK graph here.
}
result.messages().forEach(System.err::println);
```

The complete implementation is [DotFiles.java](src/main/java/example/DotFiles.java). Its sequence is:

1. Create the injector with `GraphvizDotStandaloneSetup.createInjectorAndDoEMFRegistration()`.
2. Obtain the injected `DotResourceSetProvider` and create a resource set.
3. Create a logical resource ending in `.graphviz_dot`, the extension registered by this language. Load the actual file's stream into that resource with UTF-8 encoding. The file itself can still end in `.dot`.
4. Check parse errors before using the resulting `GraphvizModel`.
5. Put the model in `DotTransformationData<GraphvizModel, ElkNode>`, call `DotImporter.transform(...)`, and read all target graphs.
6. Finalize edge containment with ELK's public `ElkGraphUtil.updateContainment(...)` helper. The importer creates connected edges without assigning their containing node. This example visits nested nodes and port edges so containment follows their endpoints' common ancestor.
7. Retain the importer's conversion messages. An invalid numeric attribute, for example, can be discarded with a message even though the DOT syntax parsed.

This imports graphs; it does not run a layout algorithm or render a diagram. ELK's [plain Java layout guide](https://www.eclipse.org/elk/documentation/tooldevelopers/usingplainjavalayout.html) describes the next layout step.

ELK's native importer does not populate `ElkNode.getIdentifier()` from DOT names. The example leaves that behavior intact and demonstrates explicit labels and edge endpoint object identity. Its CLI prints a summary of each graph's direct children and directly contained edges; the returned model also contains nested nodes and ports.

The tests cover a file path with spaces, Unicode labels, node and edge object connectivity, multiple top-level graphs, cluster/port containment, repeated imports, missing files, malformed syntax, conversion messages, and unchanged input bytes. They use small owned fixtures, not the requester's unseen files. Graphviz-specific formatting and rendering options are not guaranteed to map to ELK.

Sources: [standalone resource setup](https://github.com/eclipse-elk/elk/blob/v0.12.1/plugins/org.eclipse.elk.alg.graphviz.dot/src/org/eclipse/elk/alg/graphviz/dot/transform/DotResourceSetProvider.java), [generated extension registration](https://github.com/eclipse-elk/elk/blob/v0.12.1/plugins/org.eclipse.elk.alg.graphviz.dot/src-gen/org/eclipse/elk/alg/graphviz/dot/GraphvizDotStandaloneSetupGenerated.java), [native importer](https://github.com/eclipse-elk/elk/blob/v0.12.1/plugins/org.eclipse.elk.alg.graphviz.dot/src/org/eclipse/elk/alg/graphviz/dot/transform/DotImporter.java), and [edge containment helper](https://github.com/eclipse-elk/elk/blob/v0.12.1/plugins/org.eclipse.elk.graph/src/org/eclipse/elk/graph/util/ElkGraphUtil.java).

## Optional coffee

The example is free. If it helps, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
