module message
    implicit none
    private
    public :: value

contains

    integer function value()
        value = 42
    end function value
end module message
