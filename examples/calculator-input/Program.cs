using System;

class Calculator
{
    static void Main()
    {
        while (true)
        {
            float? first = ReadNumber("First number: ");
            if (!first.HasValue)
                return;

            string operation = ReadOperation();
            if (operation == null)
                return;

            if (operation == "sqrt")
            {
                if (first.Value < 0)
                    Console.WriteLine("Square root requires a nonnegative number.");
                else
                    Console.WriteLine("Result: sqrt({0}) = {1}", first.Value, Math.Sqrt(first.Value));
                continue;
            }

            float? second;
            while (true)
            {
                second = ReadNumber("Second number: ");
                if (!second.HasValue)
                    return;
                if ((operation == "/" || operation == "%") && second.Value == 0)
                {
                    Console.WriteLine("The divisor cannot be zero.");
                    continue;
                }
                break;
            }

            float result;
            switch (operation)
            {
                case "+": result = first.Value + second.Value; break;
                case "-": result = first.Value - second.Value; break;
                case "*": result = first.Value * second.Value; break;
                case "/": result = first.Value / second.Value; break;
                default: result = first.Value % second.Value; break;
            }
            if (float.IsNaN(result) || float.IsInfinity(result))
                Console.WriteLine("Result is outside the finite Single range.");
            else
                Console.WriteLine("Result: {0} {1} {2} = {3}", first.Value, operation, second.Value, result);
        }
    }

    static float? ReadNumber(string prompt)
    {
        while (true)
        {
            Console.Write(prompt);
            string text = Console.ReadLine();
            if (text == null)
                return null;
            float value;
            if (float.TryParse(text, out value) && !float.IsNaN(value) && !float.IsInfinity(value))
                return value;
            Console.WriteLine("Enter a finite number.");
        }
    }

    static string ReadOperation()
    {
        while (true)
        {
            Console.Write("Operation (+, -, *, /, %, sqrt): ");
            string text = Console.ReadLine();
            if (text == null)
                return null;
            string operation = text.Trim().ToLowerInvariant();
            if (operation == "+" || operation == "-" || operation == "*" ||
                operation == "/" || operation == "%" || operation == "sqrt")
                return operation;
            Console.WriteLine("Choose +, -, *, /, %, or sqrt.");
        }
    }
}
