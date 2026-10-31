#include <qapplication.h>
#include <qboxlayout.h>
#include <qcheckbox.h>
#include <qcombobox.h>
#include <qfontinfo.h>
#include <qjsonarray.h>
#include <qjsondocument.h>
#include <qjsonobject.h>
#include <qlabel.h>
#include <qlineedit.h>
#include <qpushbutton.h>
#include <qstyle.h>
#include <qstylefactory.h>
#include <qtimer.h>
#include <qwidget.h>

#include <array>
#include <iostream>
#include <link.h>
#include <string>

static int collectLibraries(dl_phdr_info *info, size_t, void *destination)
{
   const std::string path = info->dlpi_name;
   if (path.find("CsCore") != std::string::npos || path.find("CsGui") != std::string::npos ||
         path.find("libQt") != std::string::npos) {
      static_cast<QJsonArray *>(destination)->append(QString::fromUtf8(path.c_str()));
   }
   return 0;
}

int main(int argc, char **argv)
{
   QApplication app(argc, argv);

   QWidget window;
   window.setObjectName("window");
   auto *layout = new QVBoxLayout(&window);
   auto *label = new QLabel("Sample label", &window);
   label->setObjectName("label");
   auto *button = new QPushButton("Sample action", &window);
   button->setObjectName("button");
   auto *lineEdit = new QLineEdit("Sample input", &window);
   lineEdit->setObjectName("lineEdit");
   auto *comboBox = new QComboBox(&window);
   comboBox->setObjectName("comboBox");
   comboBox->addItem("First choice");
   comboBox->addItem("Second choice");
   auto *checkBox = new QCheckBox("Sample check", &window);
   checkBox->setObjectName("checkBox");
   const std::array<QWidget *, 6> widgets = {&window, label, button, lineEdit, comboBox, checkBox};
   for (auto *widget : widgets) {
      if (widget != &window) {
         layout->addWidget(widget);
      }
   }

   QJsonArray records;
   QJsonObject contents;
   int callbackCount = 0;
   window.show();
   QTimer::singleShot(50, [&]() {
      ++callbackCount;
      for (auto *widget : widgets) {
         widget->ensurePolished();
         const QFont requested = widget->font();
         const QFontInfo matched = widget->fontInfo();
         records.append(QJsonObject {
            {"name", widget->objectName()},
            {"requestedFamily", requested.family()},
            {"requestedPointSize", requested.pointSizeF()},
            {"requestedPixelSize", requested.pixelSize()},
            {"matchedFamily", matched.family()},
            {"matchedPointSize", matched.pointSizeF()},
            {"matchedPixelSize", matched.pixelSize()},
            {"visible", widget->isVisible()},
            {"polished", widget->testAttribute(Qt::WA_WState_Polished)}
         });
      }
      QJsonArray items;
      for (int index = 0; index < comboBox->count(); ++index) {
         items.append(comboBox->itemText(index));
      }
      contents = QJsonObject {
         {"label", label->text()}, {"button", button->text()}, {"lineEdit", lineEdit->text()},
         {"comboBox", items}, {"checkBox", checkBox->text()}
      };
      app.exit(0);
   });

   // The final report is emitted only after the real event loop has returned.
   const int eventLoopExit = app.exec();
   QJsonArray libraries;
   dl_iterate_phdr(collectLibraries, &libraries);
   const QJsonObject report {
      {"version", QString::fromUtf8(csVersion())},
      {"platform", QApplication::platformName()},
      {"style", app.style()->objectName()},
      {"availableStyles", QJsonArray::fromStringList(QStyleFactory::keys())},
      {"styleSheet", app.styleSheet()},
      {"libraryPaths", QJsonArray::fromStringList(QCoreApplication::libraryPaths())},
      {"loadedLibraries", libraries},
      {"callbackCount", callbackCount},
      {"eventLoopExit", eventLoopExit},
      {"contents", contents},
      {"widgets", records}
   };
   std::cout << "FONT_REPORT " << QJsonDocument(report).toJson(QJsonDocument::Compact).constData() << std::endl;
   return eventLoopExit;
}
