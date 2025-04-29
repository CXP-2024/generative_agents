
gpt_response = "     complete,   morning routine)"

cr = gpt_response.strip()
if "(" in gpt_response: 
    gpt_response = gpt_response.split("(")[-1]
    
cr = [i.strip() for i in cr.split(")")[0].split(",")]
# if has 3 elements, then remove the first one
if len(cr) == 3: 
  cr = cr[1:]
      
print(cr)
print("\033[1;32moutput: ☀️🧴\033[0m")