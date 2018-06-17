#-----------------------------------------------------------------------------
#Copyright (c) 2018 Daniel Holanda Noronha, Bahar Salehpour, Steve Wilton
#{danielhn,bahars,stevew}@ece.ubc.ca
#Permission to use, copy, and modify this software and its documentation is
#hereby granted only under the following terms and conditions. Both the
#above copyright notice and this permission notice must appear in all copies
#of the software, derivative works or modified versions, and any portions
#thereof, and both notices must appear in supporting documentation.
#This software may be distributed (but not offered for sale or transferred
#for compensation) to third parties, provided such third parties agree to
#abide by the terms and conditions of this notice.
#THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHORS, AS
#WELL AS THE UNIVERSITY OF BRITISH COLUMBIA DISCLAIM ALL
#WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
#AUTHORS OR THE UNIVERSITY OF BRITISH COLUMBIA OR THE
#UNIVERSITY OF SYDNEY BE LIABLE FOR ANY SPECIAL, DIRECT,
#INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
#WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR
#PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
#OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
#WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#---------------------------------------------------------------------------


import sys, json

# Reorder other instructions based on a instruction that was removed
def instrReorder(instr):

    # Find current and max instruction
    curr_instr=instr.split()[0][1:instr.find("=")-1]
    for i in reversed(ir):
        if i.split():
            if i.split()[0][0]=="%":
                if i.split()[0][1:i.find("=")-1].isdigit():
                    max_instr=i.split()[0][1:i.find("=")-1]
                    break

    # Reorder instructions
    for i in range(int(curr_instr)+1,int(max_instr)+1):
        for idx,j in enumerate(ir):
            if "%"+str(i) in ir[idx]:
                safeReplace("%"+str(i),"%"+str(i-1),idx)

#SafeReplace
def safeReplace(old, new, idx):
    ir[idx]=ir[idx].replace(old+" ",new+" ")
    ir[idx]=ir[idx].replace(old+",",new+",")
    ir[idx]=ir[idx].replace(old+"\n",new+"\n")
    ir[idx]=ir[idx].replace(old+")",new+")")

# Checks if arg is in intruction
def safeCheckArg(arg, instr):
    if (arg+" " in instr) or (arg+"," in instr) or (arg+"\n" in instr) or (arg+")" in instr):
        return True
    else:
        return False

# Deletes instruction and passes references to the rest of the IR
def safelyDelete(parameter,key_operation,is_global=False):
    keep_looking=True
    while keep_looking:
        keep_looking=False

        # Check if there is a case where the parameter is used that matches the key operation
        for instr in ir:
            if (parameter in instr) and (key_operation in instr) and ("metadata" not in instr):
                instruction_to_process=instr
                keep_looking=True
                break

        # If there is,  
        if keep_looking:
            # Remove that instruction
            ir.remove(instruction_to_process)

            # reconstruct calls 
            for idx,instr in enumerate(ir):
                if instruction_to_process.split()[0] in instr:
                    if is_global:
                        safeReplace(instruction_to_process.split()[0],"@"+parameter,idx)
                    else:
                        safeReplace(instruction_to_process.split()[0],"%"+parameter,idx)
                    

            # and reorder getelementptr
            if instruction_to_process.split()[0][1:].isdigit():
                instrReorder(instruction_to_process)

# Deletes instruction and passes references to the rest of the IR
def safelyDeleteNamed(parameter,key_operation):
    keep_looking=True
    while keep_looking:
        keep_looking=False

        # Check if there is a case where the parameter is used that matches the key operation and is named (not a normal operation)
        for instr in ir:
            if (parameter in instr) and (key_operation in instr) and ("metadata" not in instr) and not instr.split()[0][1:].isdigit():
                instruction_to_process=instr
                keep_looking=True
                break

        # If there is,  
        if keep_looking:
            # Remove that instruction
            ir.remove(instruction_to_process)

            # reconstruct calls 
            for idx,instr in enumerate(ir):
                if instruction_to_process.split()[0] in instr:
                    safeReplace(instruction_to_process.split()[0],"@"+parameter,idx)

# Transforms inputs to global variables
def promoteParamsToGlobal():
    # Very similar to promoteTempsToGlobal
    safelyDelete("params","getelementptr")
    safelyDelete("params","bitcast")
    safelyDelete("params","load")
    safelyDelete("params","getelementptr")

    # Transform bitcast to params into global variables
    keep_looking=True
    temps_counter=0
    while keep_looking:
        keep_looking=False
        for instr in ir[:]:
            # Try to find a load to temps
            if ("%params" in instr) and ("bitcast" in instr) and ("metadata" not in instr):
                arg=instr.split()[0]
                arg_type=instr[instr.find(" to ")+4:-2]
                keep_looking=True

                # If found, we then insert them as a global variable and remove it from its previous location
                ir.insert(4,"@param"+str(temps_counter)+" = global "+arg_type+" zeroinitializer, align 8\n")
                ir.remove(instr)
                break
        
        # Make sure to update all references to this temporary variable
        if keep_looking:
            for idx,x in enumerate(ir):
                if safeCheckArg(arg,x):
                    safeReplace(arg,"@param"+str(temps_counter),idx)

            temps_counter=temps_counter+1
        
            # Finally, reorder the instructions
            if arg[1:].isdigit():
                instrReorder(instr)

    return temps_counter

# Transforms inputs to global variables
def promoteTempsToGlobal():
    # The sequence is gep (optional), load to temps, gep (optional), bitcast to real type
    # We use the following operations to get "temps" in the bitcast to real var
    safelyDelete("temps","getelementptr")
    safelyDelete("temps","bitcast")
    safelyDelete("temps","load")
    safelyDelete("temps","getelementptr")
    
    # Transform bitcast to temps into global variables
    keep_looking=True
    temps_counter=0
    while keep_looking:
        keep_looking=False
        for instr in ir[:]:
            # Try to find a load to temps
            if ("%temps" in instr) and ("bitcast" in instr) and ("metadata" not in instr):
                arg=instr.split()[0]
                arg_type=instr[instr.find(" to ")+4:-2]
                keep_looking=True

                # If found, we then insert them as a global variable and remove it from its previous location
                ir.insert(4,"@temp"+str(temps_counter)+" = global "+arg_type+" zeroinitializer, align 8\n")
                ir.remove(instr)
                break
        
        # Make sure to update all references to this temporary variable
        if keep_looking:
            for idx,x in enumerate(ir):
                if safeCheckArg(arg,x):
                    safeReplace(arg,"@temp"+str(temps_counter),idx)

            temps_counter=temps_counter+1
        
            # Finally, reorder the instructions
            if arg[1:].isdigit():
                instrReorder(instr)

    return temps_counter

    
# Even though we are able to simulate the circuit with modelsim perfectly, the
# memories that we use are not mapped as outputs of the circuit, so Quartus will
# optimize everything away. To avoid this, we return one element of the output 
# array at the end of the computation. [A more elegant solution might exist]
def processRetval(retval):

    # First, remove Tensorflow's Retval
    # The sequence is either store OR bitcast, store
    safelyDelete("retval","bitcast")
    for idx,instr in enumerate(ir):
        if "retval" in instr:
            ir.pop(idx)
            break

    # Then, get the text of the return value
    for idx,instr in enumerate(ir):
        if "@"+retval in instr:
            retval_text = instr[instr.find("["):instr.rfind("]")+1]
            break

    # Get the dataype and dimension
    if "i64" in retval_text:
        retval_dataType="i64"
    elif "i32" in retval_text:
        retval_dataType="i32"
    elif "float" in retval_text:
        retval_dataType="float"
    retval_dim=retval_text.count("[")

    for idx,instr in enumerate(ir):
        # Make sure that main instruction is returning the right datatype
        if "define void" in ir[idx]:
            ir[idx]=ir[idx].replace("define void","define "+retval_dataType)
        
        # Return the first element of the output array.
        # This is not important for modelsim, but it is important to don't get computations optimized away in Quartus
        if "ret void" in ir[idx]:
            ir[idx]=ir[idx].replace("ret void","ret "+retval_dataType+" %leflow_retval")
            ir.insert(idx, "  %leflow_retval = load volatile "+retval_dataType+"* %leflow_gep, align 4"+"\n")
            ir.insert(idx, "  %leflow_gep = getelementptr inbounds "+retval_text+"* @"+retval+", i64 0"*(retval_dim+1)+"\n")
            break

# Used to remove specific parameters from the main function
def removeArgs(l,r):
    args=l[l.find("(")+1:l.rfind(")")]
    args=[x.strip() for x in args.split(',')]
    new_l=l[:l.find("(")+1]
    removeLastComma=False
    for idx,arg in enumerate(args):
        if r not in arg:
            new_l=new_l+args[idx]+", "
            removeLastComma=True
    if removeLastComma:
        new_l=new_l[:-2]+l[l.rfind(")"):]
    else:
        new_l=new_l+l[l.rfind(")"):]
    return new_l


def restructureMainFunction(l):
    # Force first function to be the main function
    l=l[0:l.find("@")+1]+"main"+l[l.find("("):]

    # Removing params from the main function (it will be transformed to a global variable)
    l=removeArgs(l,'params')

    # We also remove temps, since it will also be transformed to a global variable
    l=removeArgs(l,'temps')

    # We also remove retval, since it will also be transformed to a global variable
    l=removeArgs(l,'retval')

    # Remove unsupported/unused parameters
    l=removeArgs(l,'prof_counters')
    l=removeArgs(l,'run_options')

    return l

# This will transform stores to the return value to volatiles
# This guarantees that the output memory is not optimized away
def processReturnStores(return_value):
    prev_instr=""
    for idx,curr_instr in enumerate(ir):
        if ((safeCheckArg(return_value,prev_instr) and ("getelementptr" in prev_instr)) or (safeCheckArg(return_value,curr_instr))) and "store" in curr_instr:
        #if return_value in prev_instr and "getelementptr" in prev_instr and "store" in curr_instr:
            ir[idx]=ir[idx].replace("store","store volatile")
        prev_instr=curr_instr[:]

    # Save return value to json file to be used later
    file = open(output_folder+'argsAndTemps.json', 'w+')
    data = { "return_value": return_value }
    json.dump(data, file)

# Make all loads to arguments volatile, so inputs are not optimized away
def processArgLoads():
    prev_instr=""
    for idx,curr_instr in enumerate(ir):
        # getelementptr with arguments are always followed by loads
        if (("param" in prev_instr and "getelementptr" in prev_instr) or ("param" in curr_instr))  and "load" in curr_instr:
            ir[idx]=ir[idx].replace("load","load volatile")
        prev_instr=curr_instr[:]

def getFolder(file):
    if "/" in file:
        return file[:file.rfind("/")+1]
    else:
        return ""
# Receive input and output files
input_file=sys.argv[1]
output_file=sys.argv[2]
output_folder=getFolder(output_file)

# Open input and output files 
f_in = open(input_file,'r')
f_out = open(output_file,'w')

# We will cache all file in an list to make it simpler to move information around
ir=[]
while True:
    # Read line by line and exit when done
    line = f_in.readline()
    if not line:
        break
    ir.append(line)

# Make sure that first function is main function and restructure it properly
idx = [i for i, s in enumerate(ir) if 'define' in s]
ir[idx[0]] = restructureMainFunction(ir[idx[0]])

# Insert blank line between globals and main
ir.insert(4,"\n")

# Promote all arguments associated with %params to a global variable
promoteParamsToGlobal()

# Promote array to temporary buffers to a global variable
num_temps = promoteTempsToGlobal()

processReturnStores("temp"+str(num_temps-1))

# Make all loads to arguments volatile, so inputs are not optimized away
processArgLoads()

# Remove Tensorflow's retval and return correct output
processRetval("temp"+str(num_temps-1))

# Write IR data back to file
for line in ir:
    # Process line
    f_out.write(line)

# Close both files
f_in.close()
f_out.close()