# define visualization elements
def vis(model, axs):
    # create axis
    ax1 = axs
    #ax1.set_title(f'Simulation of a forest fire\n'
                 #f'Time-step: {model.t}')
    ax1.set_title('VTG capacity')
    
    # model grid on first axis
    
    # VTG capacity plot on second axis
    data = model.output.variables.EtmEVsModel
    data['total_VTG_capacity'] = data['total_VTG_capacity'].astype(float)
    data.plot(ax=ax1) 
