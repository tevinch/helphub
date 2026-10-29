#![feature(extern_types)]

#[jvm::class("java.lang.String")]
impl JavaString {
    #[jvm::method]
    pub fn length(&self) -> i32 {}
}

#[jvm::class("org.rustlang.runtime.Utf8View")]
impl RustText {
    #[jvm::static_method(name = "toJavaString")]
    pub fn to_java(value: &str) -> *mut JavaString {}
}

#[cfg(feature = "wrong-constructor")]
#[jvm::bindings("java.lang.String")]
impl JavaString {
    #[jvm::constructor]
    pub fn new(value: &str) -> *mut Self {}
}

#[cfg_attr(feature = "wrong-dispatch", jvm::class("org.slf4j.Logger"))]
#[cfg_attr(not(feature = "wrong-dispatch"), jvm::interface("org.slf4j.Logger"))]
impl Logger {
    #[jvm::method]
    pub fn info(&self, message: &JavaString) {}
}

#[jvm::class("org.slf4j.LoggerFactory", rename_all = "camelCase")]
impl LoggerFactory {
    #[jvm::static_method]
    pub fn get_logger(name: &JavaString) -> *mut Logger {}
}

fn java_string(value: &str) -> *mut JavaString {
    #[cfg(feature = "wrong-constructor")]
    return JavaString::new(value);
    #[cfg(not(feature = "wrong-constructor"))]
    RustText::to_java(value)
}

fn main() {
    let owned_message = String::from("Hello β 🌍");
    unsafe {
        let name = java_string("local.example");
        let message = java_string(owned_message.as_str());
        assert_eq!((&*message).length(), 10); // Java counts UTF-16 code units.
        println!("JAVA_STRING_LENGTH={}", (&*message).length());
        let logger = LoggerFactory::get_logger(&*name);
        (&*logger).info(&*message);
        let second = java_string("second message");
        (&*logger).info(&*second);
    }
    println!("LOGGING_DONE");
}
