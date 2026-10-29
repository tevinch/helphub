import com.formdev.flatlaf.FlatDarkLaf;
import com.formdev.flatlaf.FlatLightLaf;
import com.formdev.flatlaf.ui.FlatEmptyBorder;
import java.awt.BorderLayout;
import java.awt.GridLayout;
import java.awt.Insets;
import java.util.Date;
import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.SwingUtilities;
import org.jdesktop.swingx.JXDatePicker;

/** Per-instance text padding while retaining the native date picker. */
public class DatePickerExample {
    public static void addInnerPadding(JXDatePicker picker) {
        picker.getEditor().setBorder(new FlatEmptyBorder(6, 10, 6, 10));
        picker.revalidate();
        picker.repaint();
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            FlatLightLaf.setup();
            JFrame frame = new JFrame("Date picker text padding");
            frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
            JXDatePicker marginOnly = new JXDatePicker();
            JXDatePicker padded = new JXDatePicker();
            marginOnly.setDate(new Date());
            padded.setDate(marginOnly.getDate());
            marginOnly.getEditor().setMargin(new Insets(6, 10, 6, 10));
            addInnerPadding(padded);
            JPanel fields = new JPanel(new GridLayout(2, 2, 12, 12));
            fields.setBorder(new javax.swing.border.EmptyBorder(18, 18, 18, 18));
            fields.add(new JLabel("Editor margin only"));
            fields.add(marginOnly);
            fields.add(new JLabel("Extra inner padding"));
            fields.add(padded);
            JButton theme = new JButton("Switch light / dark");
            theme.addActionListener(event -> {
                if (javax.swing.UIManager.getLookAndFeel() instanceof FlatDarkLaf) {
                    FlatLightLaf.setup();
                } else {
                    FlatDarkLaf.setup();
                }
                SwingUtilities.updateComponentTreeUI(frame);
                // A native UI update may recreate the editor. Apply after it.
                marginOnly.getEditor().setMargin(new Insets(6, 10, 6, 10));
                addInnerPadding(padded);
                frame.pack();
            });
            frame.add(fields, BorderLayout.CENTER);
            frame.add(theme, BorderLayout.SOUTH);
            frame.pack();
            frame.setLocationByPlatform(true);
            frame.setVisible(true);
        });
    }
}
