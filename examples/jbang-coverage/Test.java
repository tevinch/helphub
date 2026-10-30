///usr/bin/env jbang "$0" "$@" ; exit $?
//JAVA 25+
//DEPS org.junit.jupiter:junit-jupiter:5.11.0
//DEPS org.junit.platform:junit-platform-launcher:1.11.0
//SOURCES Build.java
//SOURCES src/test/java/**/*

import java.io.PrintWriter;
import org.junit.platform.engine.discovery.DiscoverySelectors;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;
import org.junit.platform.launcher.listeners.SummaryGeneratingListener;

void main(String... args) {
    var request = LauncherDiscoveryRequestBuilder.request()
        .selectors(DiscoverySelectors.selectPackage("example"))
        .build();
    var listener = new SummaryGeneratingListener();
    try (var session = LauncherFactory.openSession()) {
        var launcher = session.getLauncher();
        launcher.registerTestExecutionListeners(listener);
        launcher.execute(request);
    }
    var summary = listener.getSummary();
    summary.printFailuresTo(new PrintWriter(System.err), 1);
    summary.printTo(new PrintWriter(System.out));
    if (summary.getTestsFoundCount() == 0 || summary.getTestsFailedCount() > 0) {
        System.exit(1);
    }
}
