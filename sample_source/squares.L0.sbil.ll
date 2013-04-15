;# squares.L0

;## compiled manually from L0 to SBIL
;## translated manually from SBIL to LLVM


	declare i32 printf(i8*, ...)
declare i32 (i8*, ...)* @printf(i8*, ...)

	var i32 i
%i_ptr = alloca i32

	const 1
	store i   
store i32 1, i32* %i_ptr

while7:
    load i
%i7 = load i32* %i_ptr
    const 20
	cmp le
%icmp7 = icmp le i32 %i7, i32 20

	br whiletrue7, whileend7
br i1 %icmp7, label whiletrue7, label whileend7

whiletrue7:

    const "%2d %4d"
@const8 = constant [8 * i8] c"%2d %4d\00"
%const8 = getelementptr [8 * i8]* @const8, i32 0, i32 0  	; cast to i8*

    load i
%i8 = load i32* %i_ptr

    load i
%i8a = load i32* %i_ptr

    load i
%i8b = load i32* %i_ptr

	mul
%mul8 = mul i32 %i8a, %i8b

	call printf 3
%call8 = call i32 (i8*, ...)* @printf(i8* %const8, %i8, %mul8)

	pop 			; discard result
	
	load i
%i9 = load i32* %i_ptr
	const 1
	add
%add9 = i32 %i9, i32 1

	store i
store i32 %add9, i32* %i_ptr

	br           while7
br label while

whileend7:
