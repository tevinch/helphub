import com.formdev.flatlaf.FlatDarkLaf;
import com.formdev.flatlaf.FlatLightLaf;
import java.awt.Dimension;
import java.awt.Insets;
import java.awt.image.BufferedImage;
import java.io.File;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import javax.imageio.ImageIO;
import javax.swing.BorderFactory;
import javax.swing.JPanel;
import javax.swing.SwingUtilities;
import org.jdesktop.swingx.JXDatePicker;

/** Checks the native date editor's visible padding and editable value. */
public class PaddingCheck {
    private static int operations;

    public static void main(String[] args) throws Exception {
        System.setProperty("java.awt.headless", "true");
        boolean original = args.length > 0 && args[0].equals("--original");
        int scale = Integer.parseInt(System.getProperty("check.scale", "1"));
        SwingUtilities.invokeAndWait(() -> {
            try {
                for (boolean dark : new boolean[] {false, true}) {
                    if (dark) FlatDarkLaf.setup(); else FlatLightLaf.setup();
                    check(original, dark, scale);
                }
                if (operations != 2) throw new AssertionError("All four native cases must run");
                System.out.println("PASS: two native padding and date-edit workflows at scale " + scale);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        });
    }

    private static void check(boolean original, boolean dark, int scale) throws Exception {
        JXDatePicker picker = new JXDatePicker(Locale.US);
        picker.setFormats("yyyy-MM-dd");
        Date before = new SimpleDateFormat("yyyy-MM-dd").parse("2026-10-29");
        picker.setDate(before);
        Dimension oldSize = picker.getPreferredSize();
        Object outerBorder = picker.getBorder();
        Object delegate = picker.getUI();
        if (original) {
            picker.getEditor().setMargin(new Insets(6, 10, 6, 10));
        } else {
            Class.forName("DatePickerExample").getMethod("addInnerPadding", JXDatePicker.class).invoke(null, picker);
        }
        Insets actual = picker.getEditor().getInsets();
        Insets expected = new Insets(6 * scale, 10 * scale, 6 * scale, 10 * scale);
        if (!actual.equals(expected)) throw new AssertionError("Requested extra text padding " + expected + ", got " + actual);
        if (picker.getBorder() != outerBorder || picker.getUI() != delegate) throw new AssertionError("Native picker border and UI must remain");
        if (!original) {
            SwingUtilities.updateComponentTreeUI(picker);
            Class.forName("DatePickerExample").getMethod("addInnerPadding", JXDatePicker.class).invoke(null, picker);
            if (!picker.getEditor().getInsets().equals(expected)) throw new AssertionError("Padding was not restored after native UI update");
        }
        Dimension size = picker.getPreferredSize();
        if (size.height != oldSize.height + 12 * scale) throw new AssertionError("Native height did not grow with the vertical padding");
        if (size.width <= oldSize.width) throw new AssertionError("Native width did not include text padding");
        picker.setSize(size);
        picker.doLayout();
        if (picker.getEditor().getWidth() < 20 * scale + 1) throw new AssertionError("Date text has no available room");
        if (!before.equals(picker.getDate())) throw new AssertionError("Padding changed the selected date");
        picker.getEditor().setText("2026-11-30");
        picker.commitEdit();
        if (!"2026-11-30".equals(new SimpleDateFormat("yyyy-MM-dd").format(picker.getDate()))) throw new AssertionError("Date edit did not commit");
        JPanel panel = new JPanel();
        panel.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));
        panel.add(picker);
        panel.setSize(panel.getPreferredSize());
        panel.doLayout();
        picker.doLayout();
        BufferedImage image = new BufferedImage(panel.getWidth(), panel.getHeight(), BufferedImage.TYPE_INT_RGB);
        var graphics = image.createGraphics();
        panel.printAll(graphics);
        graphics.dispose();
        ImageIO.write(image, "png", new File("padding-" + scale + "-" + (dark ? "dark" : "light") + ".png"));
        operations++;
    }
}
