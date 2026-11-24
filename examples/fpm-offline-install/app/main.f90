program install_demo
    use message, only: value
    implicit none

#ifdef PIC_VARIANT
    print '(a,i0)', 'PIC: ', value()
#else
    print '(a,i0)', 'baseline: ', value()
#endif
end program install_demo
